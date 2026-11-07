from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import imagehash
import numpy as np
from PIL import Image

from .core import (
    CLASS_NAMES,
    FastTrackError,
    ImageRecord,
    build_balanced_schedule,
    canonical_json_hash,
    configure_reproducibility,
    read_csv,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
)
from .evaluation import evaluate_model, make_inference_dataset, prediction_metrics
from .training import (
    _callbacks,
    _checkpoint_metrics,
    _history_dict,
    build_fresh_model,
    compile_model,
    configure_tensorflow,
    make_training_dataset,
)


@dataclass
class PoolRow:
    path: Path
    plant: str
    label: int
    source: str
    semantic_group: str
    sha256: str
    phash: str
    component_id: str = ""
    split: str = ""


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def _path_key(value: str | Path) -> str:
    return str(Path(value).absolute())


def _manifest_hash_maps(config: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    hashes = {_path_key(row["path"]): row["sha256"].lower() for row in read_csv(Path(config["hash_registry"]))}
    phashes = {_path_key(row["path"]): row["phash"].lower() for row in read_csv(Path(config["phash_registry"]))}
    return hashes, phashes


def _source_map(config: dict[str, Any]) -> dict[str, str]:
    rows = read_csv(Path(config["source_manifest"]))
    return {_path_key(row["path"]): row["source"] for row in rows}


def _group_map(config: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for spec in config["group_manifests"]:
        rows = read_csv(Path(spec["path"]))
        if spec.get("filter_column"):
            rows = [row for row in rows if row.get(spec["filter_column"]) == spec["filter_value"]]
        for row in rows:
            path_value = row.get(spec["path_column"], "")
            group_value = row.get(spec["group_column"], "")
            if path_value and group_value:
                path = Path(path_value)
                plant = row.get("plant", "")
                # The same chrysanthemum tree exists in the V1 and V2
                # manifests under different group naming conventions. Tree ID
                # is the trusted source identity and must cross manifest roots.
                tree_match = re.search(r"Tree(\d+)", path.name, flags=re.IGNORECASE)
                if plant == "chrysanthemum" and tree_match:
                    canonical_group = f"chrysanthemum_tree::{int(tree_match.group(1)):03d}"
                else:
                    # Roboflow exports several augmented files from one source
                    # image. The content hash suffix is an augmentation ID, not
                    # a new capture/session identity.
                    roboflow_match = re.match(r"(.+)_jpg\.rf\.[0-9a-f]+$", path.stem, flags=re.IGNORECASE)
                    if roboflow_match:
                        canonical_group = f"roboflow_original::{roboflow_match.group(1).lower()}"
                    else:
                        canonical_group = f"{spec['group_prefix']}::{group_value}"
                mapping[_path_key(path_value)] = canonical_group
    return mapping


def _phash(path: Path) -> str:
    with Image.open(path) as image:
        return str(imagehash.phash(image.convert("RGB"), hash_size=8))


def load_pool(config: dict[str, Any]) -> tuple[list[PoolRow], dict[str, Any]]:
    rows = read_csv(Path(config["training_pool_manifest"]))
    if tuple(config["classes"]) != CLASS_NAMES:
        raise FastTrackError("Exploratory class order differs from the locked six-class order")
    hash_map, phash_map = _manifest_hash_maps(config)
    source_map = _source_map(config)
    group_map = _group_map(config)
    output: list[PoolRow] = []
    missing_groups: list[str] = []
    computed_hashes = 0
    computed_phashes = 0
    missing_files: list[str] = []
    for index, row in enumerate(rows, start=1):
        path = Path(row["path"])
        key = _path_key(path)
        if not path.is_file():
            missing_files.append(str(path))
            continue
        group = group_map.get(key)
        if not group:
            missing_groups.append(str(path))
            continue
        sha = hash_map.get(key)
        if not sha:
            sha = sha256_file(path)
            computed_hashes += 1
        phash = phash_map.get(key)
        if not phash:
            phash = _phash(path)
            computed_phashes += 1
        source = source_map.get(key, row.get("v3_source", "unknown"))
        plant = row["plant"]
        if plant not in CLASS_NAMES or int(row["label"]) != CLASS_NAMES.index(plant):
            raise FastTrackError(f"Class mapping mismatch at pool row {index + 1}")
        output.append(PoolRow(path, plant, int(row["label"]), source, group, sha, phash))
    audit = {
        "pool_manifest_rows": len(rows),
        "loaded_rows": len(output),
        "missing_files": missing_files[:20],
        "missing_file_count": len(missing_files),
        "missing_group_examples": missing_groups[:20],
        "missing_group_count": len(missing_groups),
        "computed_sha256_count": computed_hashes,
        "computed_phash_count": computed_phashes,
        "semantic_group_count": len({row.semantic_group for row in output}),
        "class_counts": dict(Counter(row.plant for row in output)),
        "source_counts": dict(Counter(row.source for row in output)),
    }
    if missing_files or missing_groups or len(output) != len(rows):
        raise FastTrackError(f"Exploratory pool metadata is incomplete: {json.dumps(audit, ensure_ascii=False)}")
    return output, audit


def _union_groups_and_duplicates(
    rows: Sequence[PoolRow], distance_limit: int
) -> tuple[UnionFind, dict[str, Any], set[int]]:
    union = UnionFind(len(rows))
    group_first: dict[str, int] = {}
    sha_first: dict[str, int] = {}
    exact_pairs = 0
    cross_class_exact: list[dict[str, Any]] = []
    cross_class_semantic_groups: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if row.semantic_group in group_first:
            other = group_first[row.semantic_group]
            if row.plant != rows[other].plant:
                cross_class_semantic_groups.append(
                    {"group": row.semantic_group, "left": str(rows[other].path), "right": str(row.path)}
                )
            # One observer/source may legitimately contain multiple plant
            # classes. This is source-related, not a label conflict; keep the
            # full source group in one split component.
            union.union(index, other)
        else:
            group_first[row.semantic_group] = index
        if row.sha256 in sha_first:
            other = sha_first[row.sha256]
            exact_pairs += 1
            if row.plant != rows[other].plant:
                cross_class_exact.append(
                    {"sha256": row.sha256, "left": str(rows[other].path), "right": str(row.path)}
                )
            else:
                union.union(index, other)
        else:
            sha_first[row.sha256] = index

    values = np.asarray([int(row.phash, 16) for row in rows], dtype=np.uint64)
    near_pairs = 0
    same_class_near = 0
    source_related_near = 0
    phash_similarity_only = 0
    phash_similarity_only_indexes: set[int] = set()
    phash_similarity_only_pairs: list[dict[str, Any]] = []
    cross_class_near: list[dict[str, Any]] = []
    for index in range(len(rows) - 1):
        xor = np.bitwise_xor(values[index + 1 :], values[index])
        if hasattr(np, "bitwise_count"):
            distances = np.bitwise_count(xor)
        else:
            distances = np.unpackbits(xor.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)
        matches = np.nonzero(distances <= distance_limit)[0]
        for offset in matches:
            other = index + 1 + int(offset)
            distance = int(distances[int(offset)])
            near_pairs += 1
            if rows[index].plant != rows[other].plant:
                cross_class_near.append(
                    {
                        "left": str(rows[index].path),
                        "left_plant": rows[index].plant,
                        "right": str(rows[other].path),
                        "right_plant": rows[other].plant,
                        "distance": distance,
                    }
                )
                # Cross-class pHash similarity is never unioned automatically.
                # It requires explicit visual adjudication tied to the source audit.
                continue
            same_class_near += 1
            if rows[index].semantic_group == rows[other].semantic_group:
                source_related_near += 1
            elif rows[index].sha256 != rows[other].sha256:
                phash_similarity_only += 1
                phash_similarity_only_indexes.update((index, other))
                phash_similarity_only_pairs.append(
                    {
                        "pair_id": f"same-class-{phash_similarity_only:04d}",
                        "plant": rows[index].plant,
                        "left_path": str(rows[index].path),
                        "right_path": str(rows[other].path),
                        "left_group": rows[index].semantic_group,
                        "right_group": rows[other].semantic_group,
                        "phash_distance": distance,
                    }
                )
            # Only trusted semantic groups or exact SHA duplicates are joined.
            # A pHash-only relation is not proof of duplication and can create
            # very large transitive components. Keep both endpoints out of the
            # debug split instead of using similarity to invent a group.
            if rows[index].semantic_group == rows[other].semantic_group or rows[index].sha256 == rows[other].sha256:
                union.union(index, other)
    return union, {
        "semantic_groups": len(group_first),
        "cross_class_semantic_group_count": len(cross_class_semantic_groups),
        "cross_class_semantic_group_examples": cross_class_semantic_groups[:50],
        "exact_duplicate_pairs": exact_pairs,
        "cross_class_exact_duplicate_count": len(cross_class_exact),
        "cross_class_exact_duplicate_examples": cross_class_exact[:50],
        "near_duplicate_pairs_at_or_below_limit": near_pairs,
        "same_class_near_candidate_pairs": same_class_near,
        "same_class_source_related_pairs": source_related_near,
        "same_class_phash_similarity_only_pairs": phash_similarity_only,
        "same_class_phash_similarity_only_examples": phash_similarity_only_pairs,
        "cross_class_near_duplicate_count": len(cross_class_near),
        "cross_class_near_duplicate_examples": cross_class_near,
    }, phash_similarity_only_indexes


def _adjudicate_cross_class_candidates(
    config: dict[str, Any], duplicate_audit: dict[str, Any]
) -> tuple[dict[str, Any], set[frozenset[str]]]:
    adjudication_path = Path(config["cross_class_adjudication"])
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    source_audit_path = Path(adjudication["source_audit_path"])
    actual_source_hash = sha256_file(source_audit_path)
    if actual_source_hash != adjudication["source_audit_sha256"]:
        raise FastTrackError("Cross-class adjudication source audit hash does not match")
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    source_pairs = source_audit["cross_class_near_duplicate_examples"]
    current_pairs = duplicate_audit["cross_class_near_duplicate_examples"]
    decisions = adjudication["pairs"]
    if not (len(source_pairs) == len(current_pairs) == len(decisions)):
        raise FastTrackError("Cross-class adjudication pair count does not match the current audit")
    allowed_false_collisions: set[frozenset[str]] = set()
    counts = Counter()
    valid_decisions = {"false_phash_collision", "true_duplicate", "label_issue", "uncertain"}
    for index, (source, current, decision) in enumerate(zip(source_pairs, current_pairs, decisions, strict=True), start=1):
        expected_id = f"cross-class-{index:03d}"
        if decision.get("pair_id") != expected_id or decision.get("decision") not in valid_decisions:
            raise FastTrackError(f"Invalid adjudication row {expected_id}")
        source_key = frozenset((source["left"], source["right"]))
        current_key = frozenset((current["left"], current["right"]))
        if source_key != current_key or source["distance"] != current["distance"]:
            raise FastTrackError(f"Current pHash pair differs from adjudicated source at {expected_id}")
        counts[decision["decision"]] += 1
        if decision["decision"] == "false_phash_collision":
            allowed_false_collisions.add(current_key)
    receipt = {
        "adjudication_path": str(adjudication_path),
        "adjudication_sha256": sha256_file(adjudication_path),
        "source_audit_path": str(source_audit_path),
        "source_audit_sha256": actual_source_hash,
        "decision_counts": dict(counts),
        "all_pairs_resolved_as_false_collisions": len(allowed_false_collisions) == len(current_pairs),
        "phash_threshold_changed": False,
    }
    return receipt, allowed_false_collisions


def _adjudicate_same_class_candidates(
    config: dict[str, Any],
    duplicate_audit: dict[str, Any],
    rows: Sequence[PoolRow],
    union: UnionFind,
) -> tuple[dict[str, Any], set[frozenset[str]], set[int]]:
    adjudication_path = Path(config["same_class_adjudication"])
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    metrics_path = Path(adjudication["source_metrics_csv"])
    if sha256_file(metrics_path) != adjudication["source_metrics_csv_sha256"]:
        raise FastTrackError("Same-class adjudication metrics CSV hash does not match")
    current_pairs = duplicate_audit["same_class_phash_similarity_only_examples"]
    decisions = adjudication["pairs"]
    if len(current_pairs) != len(decisions):
        raise FastTrackError("Same-class adjudication pair count does not match the current audit")
    path_to_index = {str(row.path): index for index, row in enumerate(rows)}
    allowed_false_collisions: set[frozenset[str]] = set()
    quarantine_indexes: set[int] = set()
    counts = Counter()
    valid_decisions = {"false_phash_collision", "true_duplicate", "label_issue", "uncertain"}
    comparison_fields = (
        "pair_id", "plant", "left_path", "right_path", "left_group", "right_group", "phash_distance"
    )
    for current, decision in zip(current_pairs, decisions, strict=True):
        if decision.get("decision") not in valid_decisions:
            raise FastTrackError(f"Invalid same-class decision at {current['pair_id']}")
        if any(str(current[field]) != str(decision.get(field)) for field in comparison_fields):
            raise FastTrackError(f"Same-class adjudication differs from current audit at {current['pair_id']}")
        left_index = path_to_index[current["left_path"]]
        right_index = path_to_index[current["right_path"]]
        pair_key = frozenset((current["left_path"], current["right_path"]))
        counts[decision["decision"]] += 1
        if decision["decision"] == "false_phash_collision":
            allowed_false_collisions.add(pair_key)
        elif decision["decision"] == "true_duplicate":
            union.union(left_index, right_index)
        elif decision["decision"] == "uncertain":
            quarantine_indexes.update((left_index, right_index))
    receipt = {
        "adjudication_path": str(adjudication_path),
        "adjudication_sha256": sha256_file(adjudication_path),
        "source_metrics_csv": str(metrics_path),
        "source_metrics_csv_sha256": adjudication["source_metrics_csv_sha256"],
        "decision_counts": dict(counts),
        "quarantined_endpoint_count": len(quarantine_indexes),
        "phash_threshold_changed": False,
    }
    return receipt, allowed_false_collisions, quarantine_indexes


def prepare_internal_debug_split(
    config: dict[str, Any], output_dir: Path
) -> tuple[list[ImageRecord], list[ImageRecord], dict[str, Any]]:
    if output_dir.exists():
        raise FastTrackError(f"Refusing to overwrite split directory: {output_dir}")
    output_dir.mkdir(parents=True)
    rows, pool_audit = load_pool(config)
    write_json(output_dir / "pool_audit.json", pool_audit)
    planned_debug_targets = {
        plant: max(
            int(config["split"]["minimum_debug_per_class"]),
            round(pool_audit["class_counts"][plant] * float(config["split"]["internal_debug_fraction"])),
        )
        for plant in CLASS_NAMES
    }
    distance_limit = int(config["split"]["near_duplicate_phash_distance"])
    union, duplicate_audit, phash_similarity_only_indexes = _union_groups_and_duplicates(rows, distance_limit)
    if duplicate_audit["cross_class_exact_duplicate_count"]:
        write_json(
            output_dir / "blocked_cross_class_identity_conflicts.json",
            {
                **duplicate_audit,
                "pool_audit": pool_audit,
                "planned_debug_targets_before_component_overshoot": planned_debug_targets,
                "training_started": False,
            },
        )
        raise FastTrackError("Cross-class exact-SHA conflicts were found")
    adjudication_receipt, allowed_false_collisions = _adjudicate_cross_class_candidates(config, duplicate_audit)
    write_json(output_dir / "cross_class_adjudication_receipt.json", adjudication_receipt)
    if not adjudication_receipt["all_pairs_resolved_as_false_collisions"]:
        write_json(
            output_dir / "blocked_unresolved_cross_class_candidates.json",
            {
                **duplicate_audit,
                "adjudication": adjudication_receipt,
                "training_started": False,
            },
        )
        raise FastTrackError("Cross-class candidates include true duplicate, label issue, or uncertain decisions")
    same_class_receipt, allowed_same_class_collisions, quarantine_indexes = _adjudicate_same_class_candidates(
        config, duplicate_audit, rows, union
    )
    write_json(output_dir / "same_class_adjudication_receipt.json", same_class_receipt)
    if same_class_receipt["decision_counts"].get("label_issue", 0):
        write_json(
            output_dir / "blocked_same_class_label_issues.json",
            {"adjudication": same_class_receipt, "training_started": False},
        )
        raise FastTrackError("Same-class adjudication contains label issues")
    allowed_phash_collisions = allowed_false_collisions | allowed_same_class_collisions

    components: dict[int, list[int]] = defaultdict(list)
    for index in range(len(rows)):
        components[union.find(index)].append(index)
    component_rows: list[dict[str, Any]] = []
    for component_number, indexes in enumerate(components.values(), start=1):
        sources = Counter(rows[index].source for index in indexes)
        component_rows.append({
            "id": f"component_{component_number:05d}",
            "indexes": indexes,
            "class_counts": Counter(rows[index].plant for index in indexes),
            "primary_source": sources.most_common(1)[0][0],
            "debug_excluded_phash_similarity_only": any(
                index in quarantine_indexes for index in indexes
            ),
        })

    rng = random.Random(int(config["seed"]))
    debug_components: set[str] = set()
    targets = dict(planned_debug_targets)
    selected_counts = Counter()
    target_shortfall_due_to_quarantine: dict[str, int] = {}
    remaining = list(component_rows)
    rng.shuffle(remaining)
    remaining.sort(
        key=lambda item: hashlib.sha256(
            f"{config['seed']}::{item['primary_source']}::{item['id']}".encode()
        ).hexdigest()
    )
    while any(selected_counts[plant] < targets[plant] for plant in CLASS_NAMES):
        deficits = {plant: max(0, targets[plant] - selected_counts[plant]) for plant in CLASS_NAMES}
        scored: list[tuple[float, int, int, str, dict[str, Any]]] = []
        for component in remaining:
            if component["debug_excluded_phash_similarity_only"]:
                continue
            coverage = sum(
                min(deficits[plant], int(component["class_counts"].get(plant, 0))) for plant in CLASS_NAMES
            )
            if coverage == 0:
                continue
            size = len(component["indexes"])
            scored.append((coverage / size, coverage, -size, component["id"], component))
        if not scored:
            minimum_debug = int(config["split"]["minimum_debug_per_class"])
            below_minimum = {
                plant: minimum_debug - selected_counts[plant]
                for plant in CLASS_NAMES
                if selected_counts[plant] < minimum_debug
            }
            if below_minimum:
                raise FastTrackError(
                    f"Unable to satisfy minimum internal debug coverage after quarantine: {below_minimum}"
                )
            target_shortfall_due_to_quarantine = {
                plant: deficit for plant, deficit in deficits.items() if deficit > 0
            }
            break
        chosen = max(scored, key=lambda item: item[:4])[4]
        debug_components.add(chosen["id"])
        selected_counts.update(chosen["class_counts"])
        remaining.remove(chosen)

    component_id_by_index: dict[int, str] = {}
    for component in component_rows:
        component_id = component["id"]
        split = "internal_debug" if component_id in debug_components else "exploratory_train"
        for index in component["indexes"]:
            rows[index].component_id = component_id
            rows[index].split = split
            component_id_by_index[index] = component_id

    train_rows = [row for row in rows if row.split == "exploratory_train"]
    debug_rows = [row for row in rows if row.split == "internal_debug"]
    train_counts = Counter(row.plant for row in train_rows)
    debug_counts = Counter(row.plant for row in debug_rows)
    missing_train_classes = [plant for plant in CLASS_NAMES if train_counts[plant] < 1]
    insufficient_debug_classes = [
        plant
        for plant in CLASS_NAMES
        if debug_counts[plant] < int(config["split"]["minimum_debug_per_class"])
    ]
    if missing_train_classes or insufficient_debug_classes:
        failure = {
            "missing_train_classes": missing_train_classes,
            "insufficient_debug_classes": insufficient_debug_classes,
            "train_counts": dict(train_counts),
            "internal_debug_counts": dict(debug_counts),
            "training_started": False,
        }
        write_json(output_dir / "blocked_class_coverage.json", failure)
        raise FastTrackError(f"Exploratory split class coverage failed: {failure}")
    train_groups = {row.semantic_group for row in train_rows}
    debug_groups = {row.semantic_group for row in debug_rows}
    train_sha = {row.sha256 for row in train_rows}
    debug_sha = {row.sha256 for row in debug_rows}
    train_phash = np.asarray([int(row.phash, 16) for row in train_rows], dtype=np.uint64)
    cross_near_total = 0
    adjudicated_false_cross_split = 0
    unresolved_cross_near: list[dict[str, Any]] = []
    for debug_row in debug_rows:
        xor = np.bitwise_xor(train_phash, np.uint64(int(debug_row.phash, 16)))
        distances = np.bitwise_count(xor) if hasattr(np, "bitwise_count") else np.unpackbits(xor.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)
        for train_index in np.nonzero(distances <= distance_limit)[0]:
            train_row = train_rows[int(train_index)]
            distance = int(distances[int(train_index)])
            cross_near_total += 1
            pair_key = frozenset((str(debug_row.path), str(train_row.path)))
            if pair_key in allowed_phash_collisions:
                adjudicated_false_cross_split += 1
                continue
            unresolved_cross_near.append(
                {
                    "train_path": str(train_row.path),
                    "train_plant": train_row.plant,
                    "debug_path": str(debug_row.path),
                    "debug_plant": debug_row.plant,
                    "distance": distance,
                }
            )
    leakage = {
        "group_overlap_count": len(train_groups & debug_groups),
        "sha256_overlap_count": len(train_sha & debug_sha),
        "phash_cross_split_candidate_pairs_total": cross_near_total,
        "adjudicated_false_phash_collision_cross_split_count": adjudicated_false_cross_split,
        "unresolved_phash_cross_split_count": len(unresolved_cross_near),
        "unresolved_phash_cross_split_examples": unresolved_cross_near[:50],
        "phash_distance_limit": distance_limit,
        "phash_threshold_changed": False,
    }
    if any(leakage[key] for key in ("group_overlap_count", "sha256_overlap_count", "unresolved_phash_cross_split_count")):
        write_json(output_dir / "blocked_cross_split_leakage.json", leakage)
        raise FastTrackError(f"Cross-split leakage remains after component grouping: {leakage}")

    fields = ["path", "plant", "label", "source", "group_id", "component_id", "sha256", "phash", "split"]
    def as_dict(row: PoolRow) -> dict[str, Any]:
        return {
            "path": str(row.path), "plant": row.plant, "label": row.label, "source": row.source,
            "group_id": row.semantic_group, "component_id": row.component_id, "sha256": row.sha256,
            "phash": row.phash, "split": row.split,
        }
    train_manifest = output_dir / "exploratory_train.csv"
    debug_manifest = output_dir / "internal_debug_validation.csv"
    write_csv(train_manifest, fields, (as_dict(row) for row in train_rows))
    write_csv(debug_manifest, fields, (as_dict(row) for row in debug_rows))
    receipt = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "experiment_role": "exploratory_only",
        "passed": True,
        "pool_audit": pool_audit,
        "duplicate_audit": duplicate_audit,
        "cross_class_adjudication": adjudication_receipt,
        "same_class_adjudication": same_class_receipt,
        "cross_split_leakage": leakage,
        "target_debug_counts": targets,
        "target_shortfall_due_to_quarantine": target_shortfall_due_to_quarantine,
        "minimum_debug_per_class_preserved": int(config["split"]["minimum_debug_per_class"]),
        "train_counts": dict(train_counts),
        "internal_debug_counts": dict(debug_counts),
        "phash_similarity_only_quarantine": {
            "policy": "exclude involved semantic components from internal debug; retain in exploratory train",
            "pair_count": same_class_receipt["decision_counts"].get("uncertain", 0),
            "endpoint_count": len(quarantine_indexes),
            "excluded_component_count": sum(
                bool(component["debug_excluded_phash_similarity_only"])
                for component in component_rows
            ),
        },
        "train_source_counts": dict(Counter(row.source for row in train_rows)),
        "internal_debug_source_counts": dict(Counter(row.source for row in debug_rows)),
        "train_manifest": {"path": str(train_manifest), "sha256": sha256_file(train_manifest)},
        "internal_debug_manifest": {"path": str(debug_manifest), "sha256": sha256_file(debug_manifest)},
        "training_pool_manifest_sha256": sha256_file(Path(config["training_pool_manifest"])),
        "legacy_or_locked_test_accessed": False,
        "external_development_20_accessed": False,
    }
    write_json(output_dir / "split_receipt.json", receipt)

    def image_records(values: Sequence[PoolRow]) -> list[ImageRecord]:
        return [
            ImageRecord(row.path, row.plant, row.label, row.source, row.component_id, row.sha256, index + 2)
            for index, row in enumerate(values)
        ]
    return image_records(train_rows), image_records(debug_rows), receipt


def train_exploratory(
    config: dict[str, Any],
    train_records: Sequence[ImageRecord],
    debug_records: Sequence[ImageRecord],
    split_receipt: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    import tensorflow as tf

    if config.get("experiment_role") != "exploratory_only" or not split_receipt.get("passed"):
        raise FastTrackError("Exploratory role/split receipt is not valid")
    if output_dir.exists():
        raise FastTrackError(f"Refusing to overwrite exploratory training directory: {output_dir}")
    output_dir.mkdir(parents=True)
    seed = int(config["seed"])
    configure_reproducibility(seed)
    runtime = configure_tensorflow(config)
    schedule, sampling_receipt = build_balanced_schedule(
        train_records, seed=seed, max_repeats_per_image=int(config["sampling"]["max_repeats_per_image"])
    )
    write_json(output_dir / "sampling_receipt.json", sampling_receipt)
    batch_size = int(config["training"]["batch_size"])
    train_dataset = make_training_dataset(schedule, batch_size, seed)
    debug_dataset = make_inference_dataset(debug_records, batch_size)
    debug_labels = np.asarray([record.class_index for record in debug_records], dtype=np.int64)
    model, _ = build_fresh_model(config)
    compile_model(model, float(config["training"]["head_learning_rate"]))
    head_path = output_dir / "head_best.exploratory_only.keras"
    started = time.perf_counter()
    head_history = model.fit(
        train_dataset,
        validation_data=debug_dataset,
        epochs=int(config["training"]["head_epochs"]),
        callbacks=_callbacks(head_path, debug_dataset, debug_labels, int(config["training"]["early_stopping_patience"])),
        verbose=2,
    )
    write_json(output_dir / "head_history.json", _history_dict(head_history))
    model = tf.keras.models.load_model(head_path, compile=False)
    backbone = model.get_layer("efficientnetb0")
    backbone.trainable = True
    cutoff = max(0, len(backbone.layers) - int(config["training"]["fine_tune_tail_layers"]))
    for index, layer in enumerate(backbone.layers):
        layer.trainable = index >= cutoff and not isinstance(layer, tf.keras.layers.BatchNormalization)
    compile_model(model, float(config["training"]["fine_tune_learning_rate"]))
    fine_path = output_dir / "fine_tune_best.exploratory_only.keras"
    fine_history = model.fit(
        train_dataset,
        validation_data=debug_dataset,
        epochs=int(config["training"]["fine_tune_epochs"]),
        callbacks=_callbacks(fine_path, debug_dataset, debug_labels, int(config["training"]["early_stopping_patience"])),
        verbose=2,
    )
    write_json(output_dir / "fine_tune_history.json", _history_dict(fine_history))
    head_metrics = _checkpoint_metrics(head_path, debug_dataset, debug_labels)
    fine_metrics = _checkpoint_metrics(fine_path, debug_dataset, debug_labels)
    selected_path, selected_metrics = max(
        ((head_path, head_metrics), (fine_path, fine_metrics)),
        key=lambda item: (item[1]["macro_f1"], min(item[1]["per_class_recall"].values()), item[1]["accuracy"]),
    )
    receipt = {
        "schema_version": 1,
        "completed_at_utc": utc_now(),
        "experiment_role": "exploratory_only",
        "production_promotion_allowed": False,
        "deployment_allowed": False,
        "fresh_imagenet_initialization": True,
        "loaded_v2_to_v5_weights": False,
        "duration_seconds": time.perf_counter() - started,
        "seed": seed,
        "config_sha256": canonical_json_hash(config),
        "runtime": {**runtime, "tensorflow": tf.__version__, "keras": getattr(tf.keras, "__version__", "unknown")},
        "checkpoints": {
            "head": {"path": str(head_path), "sha256": sha256_file(head_path), "metrics": head_metrics},
            "fine_tune": {"path": str(fine_path), "sha256": sha256_file(fine_path), "metrics": fine_metrics},
            "selected_for_debug_report_only": {"path": str(selected_path), "sha256": sha256_file(selected_path), "metrics": selected_metrics},
        },
        "selection_data": "internal_debug_validation_only",
        "known_failures_used_for_selection": False,
        "external_development_20_accessed": False,
        "legacy_or_locked_test_accessed": False,
    }
    write_json(output_dir / "training_receipt.json", receipt)
    return receipt
