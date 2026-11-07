from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import imagehash
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


CLASS_NAMES = (
    "chrysanthemum",
    "marigold",
    "money_plant",
    "rose",
    "snake_plant",
    "spider_plant",
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


class RecoveryError(RuntimeError):
    pass


@dataclass
class Candidate:
    path: Path
    proposed_plant: str
    source_id: str
    source_history: str
    source_record_id: str
    source_group: str
    license_status: str
    manifest_sha256: str = ""
    manifest_phash: str = ""
    sha256: str = ""
    phash: str = ""
    width: int = 0
    height: int = 0
    quality_score: float = 0.0
    corner_std: float = 0.0
    green_fraction: float = 0.0
    decode_error: str = ""
    exact_exclusion_role: str = ""
    near_training_distance: int | None = None
    near_training_path: str = ""
    group_leakage: bool = False
    candidate_exact_duplicate: bool = False
    candidate_near_duplicate: bool = False
    selection_status: str = "not_evaluated"
    exclusion_reasons: list[str] = field(default_factory=list)
    candidate_id: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise RecoveryError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    if path.exists():
        raise RecoveryError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def choose_column(rows: Sequence[dict[str, str]], names: Sequence[str]) -> str:
    if not rows:
        raise RecoveryError("CSV is empty")
    for name in names:
        if name in rows[0]:
            return name
    raise RecoveryError(f"No column from {list(names)} found in {sorted(rows[0])}")


def normalize_path(value: str | Path) -> str:
    return os.path.normcase(os.path.abspath(str(value)))


def phash_int(value: str) -> int:
    return int(value, 16)


def hamming_distance(left: str, right: str) -> int:
    return (phash_int(left) ^ phash_int(right)).bit_count()


def min_phash_distance(value: str, references: np.ndarray) -> tuple[int | None, int | None]:
    if references.size == 0:
        return None, None
    xor = np.bitwise_xor(references, np.uint64(phash_int(value)))
    if hasattr(np, "bitwise_count"):
        distances = np.bitwise_count(xor)
    else:
        distances = np.unpackbits(xor.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)
    index = int(np.argmin(distances))
    return int(distances[index]), index


def manifest_paths(path: Path) -> list[str]:
    rows = read_csv(path)
    if not rows:
        return []
    column = choose_column(rows, ("path", "image_path", "filepath", "file_path", "local_path"))
    return [row[column] for row in rows if row.get(column)]


def inventory_manifest(path: Path) -> dict[str, Any]:
    rows = read_csv(path)
    status_columns = ("review_status", "manual_decision", "final_status", "dataset_role", "v3_split")
    plant_column = next((name for name in ("plant", "plant_code") if rows and name in rows[0]), None)
    return {
        "path": str(path),
        "rows": len(rows),
        "columns": list(rows[0]) if rows else [],
        "plant_counts": dict(Counter(row.get(plant_column, "unknown") for row in rows)) if plant_column else {},
        "status_counts": {
            column: dict(Counter(row.get(column, "") for row in rows))
            for column in status_columns
            if rows and column in rows[0]
        },
        "sha256": sha256_file(path),
    }


def find_named_plant_directories(root: Path, directory_name: str) -> list[Path]:
    if not root.is_dir():
        return []
    matches = [path for path in root.rglob(directory_name) if path.is_dir()]
    # Prefer the outermost matching directory. Recursive file traversal from
    # that directory includes nested same-named folders once, without dropping
    # sibling disease/condition directories (for example Rosa/Rosa).
    return [path for path in matches if not any(other != path and other in path.parents for other in matches)]


def _stratified_file_screen(paths: Sequence[Path], root: Path, maximum: int) -> list[Path]:
    if len(paths) <= maximum:
        return list(paths)
    by_parent: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        relative = path.relative_to(root)
        bucket = relative.parts[0] if len(relative.parts) > 1 else "root"
        by_parent[bucket].append(path)
    selected: list[Path] = []
    leftovers: list[Path] = []
    quota = max(1, maximum // len(by_parent))
    for bucket in sorted(by_parent):
        items = sorted(by_parent[bucket])
        if len(items) <= quota:
            selected.extend(items)
            continue
        chosen = {int(position) for position in np.linspace(0, len(items) - 1, quota, dtype=int)}
        selected.extend(items[position] for position in sorted(chosen))
        leftovers.extend(item for index, item in enumerate(items) if index not in chosen)
    if len(selected) < maximum:
        selected.extend(sorted(leftovers)[: maximum - len(selected)])
    return selected[:maximum]


def filesystem_source_group(source: dict[str, Any], relative: Path) -> str:
    match = re.search(source["group_regex"], str(relative), flags=re.IGNORECASE)
    group_value = match.group(1) if match else relative.stem
    return f"{source['group_namespace']}::{group_value.lower()}"


def ingest_filesystem_sources(config: dict[str, Any]) -> tuple[list[Candidate], list[dict[str, Any]]]:
    candidates: list[Candidate] = []
    discovery: list[dict[str, Any]] = []
    maximum = int(config["max_files_per_filesystem_source"])
    for source in config["filesystem_candidate_sources"]:
        plant = source["plant"]
        if plant not in CLASS_NAMES:
            raise RecoveryError(f"Unsupported plant in source config: {plant}")
        directories = find_named_plant_directories(Path(source["root"]), source["plant_directory_name"])
        for directory in directories:
            all_paths = [
                path for path in sorted(directory.rglob("*")) if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            ]
            screened_paths = _stratified_file_screen(all_paths, directory, maximum)
            discovery.append(
                {
                    "source_id": source["source_id"],
                    "plant": plant,
                    "directory": str(directory),
                    "images_discovered": len(all_paths),
                    "images_screened": len(screened_paths),
                    "screening": "deterministic_stratified_by_condition_directory",
                }
            )
            for path in screened_paths:
                relative = path.relative_to(directory)
                source_group = filesystem_source_group(source, relative)
                candidates.append(
                    Candidate(
                        path=path,
                        proposed_plant=plant,
                        source_id=source["source_id"],
                        source_history=source["source_history"],
                        source_record_id=str(relative),
                        source_group=source_group,
                        license_status=source["license_status"],
                    )
                )
    return candidates, discovery


def ingest_manifest_sources(config: dict[str, Any]) -> tuple[list[Candidate], dict[str, set[str]]]:
    candidates: list[Candidate] = []
    group_by_path: dict[str, set[str]] = defaultdict(set)
    for source in config["manifest_candidate_sources"]:
        manifest = Path(source["path"])
        rows = read_csv(manifest)
        path_column = choose_column(rows, ("path", "image_path", "filepath"))
        plant_column = choose_column(rows, ("plant", "plant_code"))
        group_column = choose_column(rows, ("duplicate_group", "group_id", "source_group"))
        for row_number, row in enumerate(rows, start=2):
            plant = row[plant_column].strip()
            if plant not in CLASS_NAMES:
                continue
            path = Path(row[path_column])
            group = row.get(group_column, "").strip() or f"{source['source_id']}::row_{row_number}"
            group_by_path[normalize_path(path)].add(group)
            candidates.append(
                Candidate(
                    path=path,
                    proposed_plant=plant,
                    source_id=source["source_id"],
                    source_history=source["source_history"],
                    source_record_id=row.get("observation_id") or row.get("number") or path.stem,
                    source_group=group,
                    license_status=source["license_status"],
                    manifest_sha256=row.get("sha256", "").lower(),
                    manifest_phash=row.get("phash", "").lower(),
                )
            )
    return candidates, group_by_path


def ingest_extra_images(config: dict[str, Any]) -> list[Candidate]:
    candidates: list[Candidate] = []
    for source in config.get("extra_image_candidates", []):
        path = Path(source["path"])
        candidates.append(
            Candidate(
                path=path,
                proposed_plant=source["plant"],
                source_id=source["source_id"],
                source_history=source["source_history"],
                source_record_id=path.name,
                source_group=f"{source['source_id']}::{path.stem}",
                license_status=source["license_status"],
            )
        )
    return candidates


def image_evidence(candidate: Candidate) -> None:
    try:
        if not candidate.sha256:
            candidate.sha256 = sha256_file(candidate.path)
        with Image.open(candidate.path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            candidate.width, candidate.height = image.size
            candidate.phash = str(imagehash.phash(image, hash_size=8))
            preview = image.copy()
            preview.thumbnail((256, 256), Image.Resampling.LANCZOS)
            array = np.asarray(preview, dtype=np.float32)
            height, width = array.shape[:2]
            border = max(2, min(height, width) // 10)
            corners = np.concatenate(
                [
                    array[:border, :border].reshape(-1, 3),
                    array[:border, -border:].reshape(-1, 3),
                    array[-border:, :border].reshape(-1, 3),
                    array[-border:, -border:].reshape(-1, 3),
                ],
                axis=0,
            )
            candidate.corner_std = float(corners.std())
            red, green, blue = array[..., 0], array[..., 1], array[..., 2]
            candidate.green_fraction = float(((green > red * 0.9) & (green > blue * 1.05) & (green > 35)).mean())
            resolution_score = min(1.0, math.log2(max(2, min(image.size))) / 10.0)
            candidate.quality_score = float(
                0.45 * resolution_score
                + 0.30 * min(1.0, candidate.corner_std / 70.0)
                + 0.25 * min(1.0, candidate.green_fraction / 0.45)
            )
    except Exception as exc:  # image decode failures must be auditable rows
        candidate.decode_error = f"{type(exc).__name__}: {exc}"


def build_exclusions(config: dict[str, Any]) -> dict[str, Any]:
    hash_rows = read_csv(Path(config["hash_registry"]))
    phash_rows = read_csv(Path(config["phash_registry"]))
    sha_role: dict[str, str] = {}
    path_role: dict[str, str] = {}
    registry_paths: set[str] = set()
    phash_values: list[int] = []
    phash_paths: list[str] = []
    for row in hash_rows:
        sha_role[row["sha256"].lower()] = row.get("source", "historical_registry")
        normalized = normalize_path(row["path"])
        registry_paths.add(normalized)
        path_role[normalized] = row.get("source", "historical_registry")
    for row in phash_rows:
        value = row.get("phash", "").strip().lower()
        if value:
            phash_values.append(phash_int(value))
            phash_paths.append(row["path"])

    training_paths = set(manifest_paths(Path(config["training_manifest"])))
    for path_value in training_paths:
        path_role[normalize_path(path_value)] = "v5_training"

    history_counts: dict[str, int] = {}
    for item in config["excluded_history_manifests"]:
        paths = manifest_paths(Path(item["path"]))
        history_counts[item["role"]] = len(paths)
        for path_value in paths:
            path_role[normalize_path(path_value)] = item["role"]
    for path_value in config.get("extra_excluded_images", []):
        path = Path(path_value)
        path_role[normalize_path(path)] = "known_failure_used_for_development"
        if path.is_file():
            sha_role[sha256_file(path)] = "known_failure_used_for_development"
            value = str(imagehash.phash(Image.open(path).convert("RGB"), hash_size=8))
            phash_values.append(phash_int(value))
            phash_paths.append(str(path))

    # V5 added 13 Marigold images after the V2 registry. Hash/pHash only V5
    # paths missing from the old registry so the exclusion set is complete.
    missing_training_registry = 0
    for path_value in training_paths:
        normalized = normalize_path(path_value)
        if normalized in registry_paths:
            continue
        path = Path(path_value)
        if not path.is_file():
            continue
        missing_training_registry += 1
        sha_role[sha256_file(path)] = "v5_training_computed"
        with Image.open(path) as image:
            value = str(imagehash.phash(image.convert("RGB"), hash_size=8))
        phash_values.append(phash_int(value))
        phash_paths.append(str(path))
        path_role[normalized] = "v5_training_computed"
    return {
        "sha_role": sha_role,
        "path_role": path_role,
        "phash_array": np.asarray(phash_values, dtype=np.uint64),
        "phash_paths": phash_paths,
        "training_paths": {normalize_path(path) for path in training_paths},
        "history_counts": history_counts,
        "hash_registry_rows": len(hash_rows),
        "phash_registry_rows": len(phash_rows),
        "missing_training_registry_computed": missing_training_registry,
    }


def contact_sheet(path: Path, candidates: Sequence[Candidate], config: dict[str, Any], title: str) -> None:
    columns = int(config["columns"])
    rows = int(config["rows"])
    thumb_width = int(config["thumbnail_width"])
    thumb_height = int(config["thumbnail_height"])
    label_height = 54
    header_height = 42
    canvas = Image.new(
        "RGB",
        (columns * thumb_width, header_height + rows * (thumb_height + label_height)),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((10, 10), title, fill="black", font=font)
    for index, candidate in enumerate(candidates[: columns * rows]):
        row, column = divmod(index, columns)
        left = column * thumb_width
        top = header_height + row * (thumb_height + label_height)
        try:
            with Image.open(candidate.path) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                fitted = ImageOps.contain(image, (thumb_width - 8, thumb_height - 8), Image.Resampling.LANCZOS)
                x = left + (thumb_width - fitted.width) // 2
                y = top + (thumb_height - fitted.height) // 2
                canvas.paste(fitted, (x, y))
        except Exception:
            draw.rectangle((left, top, left + thumb_width - 1, top + thumb_height - 1), fill="#dddddd")
        source_short = candidate.source_id[:24]
        record_short = Path(candidate.source_record_id).name[:34]
        label = (
            f"{candidate.candidate_id} | {source_short}\n"
            f"source={record_short}\n"
            f"pHashDist={candidate.near_training_distance} score={candidate.quality_score:.3f}"
        )
        draw.multiline_text((left + 4, top + thumb_height + 3), label, fill="black", font=font, spacing=2)
        draw.rectangle((left, top, left + thumb_width - 1, top + thumb_height + label_height - 1), outline="#777777")
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, quality=90)


def candidate_row(candidate: Candidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "path": str(candidate.path),
        "plant": candidate.proposed_plant,
        "proposed_plant_from_source": candidate.proposed_plant,
        "source": candidate.source_id,
        "source_record_id": candidate.source_record_id,
        "group_id": candidate.source_group,
        "source_history": candidate.source_history,
        "license_status": candidate.license_status,
        "sha256": candidate.sha256,
        "phash": candidate.phash,
        "width": candidate.width,
        "height": candidate.height,
        "quality_score": f"{candidate.quality_score:.6f}",
        "corner_std": f"{candidate.corner_std:.6f}",
        "green_fraction": f"{candidate.green_fraction:.6f}",
        "decode_error": candidate.decode_error,
        "exact_exclusion_role": candidate.exact_exclusion_role,
        "near_training_phash_distance": candidate.near_training_distance,
        "near_training_path": candidate.near_training_path,
        "group_leakage": str(candidate.group_leakage).lower(),
        "candidate_exact_duplicate": str(candidate.candidate_exact_duplicate).lower(),
        "candidate_near_duplicate": str(candidate.candidate_near_duplicate).lower(),
        "selection_status": candidate.selection_status,
        "exclusion_reasons": "|".join(candidate.exclusion_reasons),
        "review_status": "pending",
        "review_plant": "",
        "label_confirmed": "",
        "target_plant_visible": "",
        "single_clear_target": "",
        "leaf_sufficient": "",
        "image_quality": "",
        "natural_mobile_like": "",
        "review_notes": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover a leakage-audited development-validation candidate pool")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RecoveryError(f"Refusing to overwrite output directory: {args.output}")
    args.output.mkdir(parents=True)
    config = read_json(args.config)
    random.seed(int(config["seed"]))
    inventory = [inventory_manifest(Path(path)) for path in config["inventory_manifests"]]
    exclusions = build_exclusions(config)
    manifest_candidates, group_by_path = ingest_manifest_sources(config)
    filesystem_candidates, filesystem_discovery = ingest_filesystem_sources(config)
    candidates = manifest_candidates + filesystem_candidates + ingest_extra_images(config)
    unique_candidates: list[Candidate] = []
    seen_paths: set[str] = set()
    for candidate in candidates:
        normalized = normalize_path(candidate.path)
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        unique_candidates.append(candidate)

    leaking_groups: set[str] = set()
    for candidate in manifest_candidates:
        if normalize_path(candidate.path) in exclusions["training_paths"]:
            leaking_groups.add(candidate.source_group)
    # Reconstruct dataset-semantic groups from every historical train/eval
    # path, so a new copy of the same Tree/session cannot cross the split just
    # because its filesystem path differs.
    for source in config["filesystem_candidate_sources"]:
        if not source.get("compare_groups_to_history", False):
            continue
        required_fragment = source.get("historical_path_contains", "").lower()
        for historical_path in exclusions["path_role"]:
            if required_fragment and required_fragment not in historical_path.lower():
                continue
            match = re.search(source["group_regex"], historical_path, flags=re.IGNORECASE)
            if match:
                leaking_groups.add(f"{source['group_namespace']}::{match.group(1).lower()}")

    reference_phashes: np.ndarray = exclusions["phash_array"]
    reference_paths: list[str] = exclusions["phash_paths"]
    sha_first_candidate: dict[str, Candidate] = {}
    for index, candidate in enumerate(unique_candidates, start=1):
        if index % 250 == 0:
            print(f"AUDIT_PROGRESS {index}/{len(unique_candidates)}", flush=True)
        normalized = normalize_path(candidate.path)
        if normalized in exclusions["path_role"]:
            candidate.exact_exclusion_role = exclusions["path_role"][normalized]
            candidate.exclusion_reasons.append("path_used_by_training_or_history")
        try:
            candidate.sha256 = sha256_file(candidate.path)
        except Exception as exc:
            candidate.decode_error = f"{type(exc).__name__}: {exc}"
            candidate.exclusion_reasons.append("unreadable_file")
            continue
        if candidate.sha256 in exclusions["sha_role"]:
            candidate.exact_exclusion_role = exclusions["sha_role"][candidate.sha256]
            candidate.exclusion_reasons.append("sha256_used_by_training_or_history")
        if candidate.source_group in leaking_groups:
            candidate.group_leakage = True
            candidate.exclusion_reasons.append("source_group_intersects_training")
        if candidate.sha256 in sha_first_candidate:
            candidate.candidate_exact_duplicate = True
            candidate.exclusion_reasons.append("duplicate_within_candidate_pool")
        else:
            sha_first_candidate[candidate.sha256] = candidate
        if candidate.exclusion_reasons:
            continue
        image_evidence(candidate)
        if candidate.decode_error:
            candidate.exclusion_reasons.append("decode_error")
            continue
        distance, near_index = min_phash_distance(candidate.phash, reference_phashes)
        candidate.near_training_distance = distance
        if near_index is not None:
            candidate.near_training_path = reference_paths[near_index]
        if distance is not None and distance <= int(config["near_training_phash_distance"]):
            candidate.exclusion_reasons.append("near_duplicate_training_or_history")
        if min(candidate.width, candidate.height) < int(config["minimum_image_side"]):
            candidate.exclusion_reasons.append("image_side_below_minimum")

    selected_by_class: dict[str, list[Candidate]] = {name: [] for name in CLASS_NAMES}
    for plant in CLASS_NAMES:
        eligible = [
            candidate
            for candidate in unique_candidates
            if candidate.proposed_plant == plant and not candidate.exclusion_reasons
        ]
        eligible.sort(key=lambda item: (-item.quality_score, item.source_id, str(item.path)))
        used_groups: set[str] = set()
        selected_phashes: list[str] = []
        for candidate in eligible:
            if candidate.source_group in used_groups:
                candidate.group_leakage = True
                candidate.exclusion_reasons.append("same_source_group_as_selected_candidate")
                continue
            if selected_phashes and min(hamming_distance(candidate.phash, value) for value in selected_phashes) <= int(
                config["review_diversity_phash_distance"]
            ):
                candidate.candidate_near_duplicate = True
                candidate.exclusion_reasons.append("near_duplicate_within_review_selection")
                continue
            candidate.selection_status = "selected_for_manual_review"
            selected_by_class[plant].append(candidate)
            used_groups.add(candidate.source_group)
            selected_phashes.append(candidate.phash)
            if len(selected_by_class[plant]) >= int(config["review_candidates_per_class"]):
                break
        for candidate in eligible:
            if candidate.selection_status == "not_evaluated":
                candidate.selection_status = "eligible_not_selected"
    selected = [candidate for plant in CLASS_NAMES for candidate in selected_by_class[plant]]
    for plant in CLASS_NAMES:
        for index, candidate in enumerate(selected_by_class[plant], start=1):
            candidate.candidate_id = f"{plant}-{index:03d}"

    fields = list(candidate_row(selected[0] if selected else Candidate(Path(""), "", "", "", "", "", "")).keys())
    write_csv(args.output / "development_validation_manual_review.csv", fields, (candidate_row(item) for item in selected))
    write_csv(args.output / "candidate_audit_all.csv", fields, (candidate_row(item) for item in unique_candidates))

    sheet_config = config["contact_sheet"]
    page_size = int(sheet_config["columns"]) * int(sheet_config["rows"])
    contact_sheet_files: list[str] = []
    for plant in CLASS_NAMES:
        items = selected_by_class[plant]
        for page_start in range(0, len(items), page_size):
            page = page_start // page_size + 1
            output = args.output / "contact_sheets" / f"{plant}_review_{page:02d}.jpg"
            contact_sheet(output, items[page_start : page_start + page_size], sheet_config, f"{plant} manual review page {page}")
            contact_sheet_files.append(str(output))

    selected_counts = {plant: len(selected_by_class[plant]) for plant in CLASS_NAMES}
    approved_counts = {plant: 0 for plant in CLASS_NAMES}
    target = int(config["target_per_class"])
    technically_missing = {plant: max(0, target - selected_counts[plant]) for plant in CLASS_NAMES}
    approval_missing = {plant: target for plant in CLASS_NAMES}
    exclusion_counts = Counter(reason for candidate in unique_candidates for reason in candidate.exclusion_reasons)
    source_counts = Counter(candidate.source_id for candidate in unique_candidates)
    source_selected_counts = Counter(candidate.source_id for candidate in selected)
    report = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "status": "pending_manual_review",
        "training_unlocked": False,
        "candidate_images_scanned": len(unique_candidates),
        "candidate_source_counts": dict(source_counts),
        "filesystem_discovery": filesystem_discovery,
        "selected_for_manual_review_counts": selected_counts,
        "manual_approved_counts": approved_counts,
        "technically_missing_to_offer_20_for_review": technically_missing,
        "manual_approval_missing_to_reach_20": approval_missing,
        "selected_source_counts": dict(source_selected_counts),
        "exclusion_counts": dict(exclusion_counts),
        "leakage_policy": {
            "exact_sha256_excluded": True,
            "near_training_phash_distance_max_excluded": int(config["near_training_phash_distance"]),
            "candidate_diversity_phash_distance_max_excluded": int(config["review_diversity_phash_distance"]),
            "source_groups_intersecting_training_excluded": True,
            "legacy_validation_test_excluded": True,
            "overused_external_development_excluded": True,
        },
        "exclusion_registry": {
            "hash_registry_rows": exclusions["hash_registry_rows"],
            "phash_registry_rows": exclusions["phash_registry_rows"],
            "missing_v5_training_registry_entries_computed": exclusions["missing_training_registry_computed"],
            "history_manifest_counts": exclusions["history_counts"],
        },
        "inventory_manifests": inventory,
        "contact_sheets": contact_sheet_files,
        "limitations": [
            "Folder/source labels are proposals only; no candidate is approved automatically.",
            "License/attribution remains not verified for the Windows and Mendeley candidate sources.",
            "pHash distance is a screening tool; selected sheets still require visual duplicate adjudication.",
            "The draft cannot unlock training until at least 20 manually approved, quality-valid images exist in every class.",
        ],
    }
    write_json(args.output / "recovery_report.json", report)

    review_manifest = args.output / "development_validation_manual_review.csv"
    receipt = {
        "schema_version": 1,
        "passed": False,
        "near_duplicate_review_complete": False,
        "train_manifest_sha256": sha256_file(Path(config["training_manifest"])),
        "development_manifest_sha256": sha256_file(review_manifest),
        "notes": [
            "Draft candidates passed automated exact/path/group/pHash screening only.",
            "Manual plant identity, quality, natural/mobile likeness, licensing and visual near-duplicate review are pending.",
        ],
    }
    receipt_path = args.output / "duplicate_audit_receipt_pending.json"
    write_json(receipt_path, receipt)

    fasttrack_config = read_json(Path(config["fasttrack_config_template"]))
    development = fasttrack_config["data"]["development"]
    fasttrack_config["data"]["development_manifest"] = str(review_manifest)
    development.update(
        {
            "status": "pending_manual_review",
            "duplicate_audit_status": "pending_visual_near_duplicate_review",
            "duplicate_audit_receipt": str(receipt_path),
            "split_column": None,
            "split_value": None,
            "path_column": "path",
            "label_column": "plant",
            "source_column": "source",
            "group_column": "group_id",
            "sha_column": "sha256",
            "quality_review_manifest": str(review_manifest),
            "quality_path_column": "path",
            "required_manifest_flags": {
                "review_status": ["approved"],
                "label_confirmed": ["yes"],
                "target_plant_visible": ["yes"],
                "single_clear_target": ["yes"],
                "leaf_sufficient": ["yes"],
                "image_quality": ["good"],
                "natural_mobile_like": ["yes"],
                "license_status": ["verified", "approved"],
            },
        }
    )
    pending_config = args.output / "fresh_b0_recovery_pending.json"
    write_json(pending_config, fasttrack_config)
    print(json.dumps({"output": str(args.output), "selected_counts": selected_counts, "status": report["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
