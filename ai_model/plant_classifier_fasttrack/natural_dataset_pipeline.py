from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import stat
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import imagehash
import numpy as np
from PIL import Image, ImageDraw, ImageFont


CLASS_NAMES = (
    "chrysanthemum",
    "marigold",
    "money_plant",
    "rose",
    "snake_plant",
    "spider_plant",
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
INTAKE_FIELDS = (
    "external_id",
    "file_path",
    "plant",
    "plant_id",
    "observer_id",
    "session_id",
    "source",
    "capture_date",
    "device",
    "health_state",
    "license",
    "source_url",
    "license_url",
    "attribution",
    "natural_background",
    "notes",
)
REVIEW_FIELDS = (
    "species_confirmed",
    "leaf_visible",
    "image_quality",
    "natural_scene_confirmed",
    "license_verified",
    "review_decision",
    "reviewer",
    "review_notes",
)
PAIR_DECISIONS = {"false_phash_collision", "true_duplicate", "source_related_sample", "label_issue", "uncertain"}


class DatasetPipelineError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise DatasetPipelineError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    if path.exists():
        raise DatasetPipelineError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def phash_file(path: Path) -> str:
    with Image.open(path) as image:
        return str(imagehash.phash(image.convert("RGB"), hash_size=8))


def hamming_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def choose_column(rows: Sequence[dict[str, str]], candidates: Sequence[str]) -> str | None:
    if not rows:
        return None
    return next((name for name in candidates if name in rows[0]), None)


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip()).strip("._")
    return cleaned[:100] or "unnamed"


def semantic_keys(row: dict[str, str]) -> tuple[str, str, str]:
    source = row["source"].strip().lower()
    observer = f"{source}::observer::{row['observer_id'].strip().lower()}"
    session = f"{source}::observer::{row['observer_id'].strip().lower()}::session::{row['session_id'].strip().lower()}"
    plant = f"{source}::plant::{row['plant_id'].strip().lower()}"
    return observer, session, plant


def semantic_group(row: dict[str, str]) -> str:
    observer, session, plant = semantic_keys(row)
    return f"{observer}|{session}|{plant}"


def validate_metadata_row(row: dict[str, str], config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in INTAKE_FIELDS:
        if field != "notes" and not str(row.get(field, "")).strip():
            errors.append(f"missing_{field}")
    if row.get("plant", "").strip() not in CLASS_NAMES:
        errors.append("unsupported_plant")
    if row.get("health_state", "").strip().lower() not in config["allowed_health_states"]:
        errors.append("invalid_health_state")
    if row.get("license", "").strip().lower() not in config["allowed_licenses"]:
        errors.append("unapproved_license")
    if row.get("natural_background", "").strip().lower() not in {"yes", "true", "1"}:
        errors.append("not_declared_natural_background")
    try:
        date.fromisoformat(row.get("capture_date", ""))
    except ValueError:
        errors.append("invalid_capture_date")
    path = Path(row.get("file_path", ""))
    if not path.is_file():
        errors.append("file_missing")
    elif path.suffix.lower() not in IMAGE_SUFFIXES:
        errors.append("unsupported_image_type")
    if row.get("license", "").strip().lower() != "own_photo":
        if not row.get("source_url", "").strip() or not row.get("license_url", "").strip():
            errors.append("external_source_requires_source_and_license_urls")
        if not row.get("attribution", "").strip():
            errors.append("external_source_requires_attribution")
    return sorted(set(errors))


def image_info(path: Path) -> tuple[int, int, str]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            image.convert("RGB")
        return width, height, ""
    except Exception as exc:  # Pillow raises format-specific exception types.
        return 0, 0, f"{type(exc).__name__}: {exc}"


def _font(size: int):
    for path in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    try:
        with Image.open(path) as source:
            image = source.convert("RGB")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", size, "white")
        canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
        return canvas
    except Exception:
        canvas = Image.new("RGB", size, "#dddddd")
        ImageDraw.Draw(canvas).text((8, 8), "IMAGE ERROR", fill="red", font=_font(16))
        return canvas


def contact_sheets(rows: Sequence[dict[str, Any]], output_dir: Path, config: dict[str, Any], prefix: str) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    settings = config["contact_sheet"]
    columns, page_rows = int(settings["columns"]), int(settings["rows"])
    image_width, image_height = int(settings["thumbnail_width"]), int(settings["thumbnail_height"])
    page_size = columns * page_rows
    output_paths: list[str] = []
    for page_index in range(math.ceil(len(rows) / page_size)):
        page = rows[page_index * page_size : (page_index + 1) * page_size]
        caption_height, title_height = 82, 48
        canvas = Image.new(
            "RGB",
            (columns * image_width, title_height + page_rows * (image_height + caption_height)),
            "white",
        )
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 9), f"{prefix} — page {page_index + 1}", fill="black", font=_font(23))
        for index, row in enumerate(page):
            x = (index % columns) * image_width
            y = title_height + (index // columns) * (image_height + caption_height)
            canvas.paste(_fit_image(Path(row["staged_path"]), (image_width, image_height)), (x, y))
            caption = (
                f"{row['candidate_id']} | {row['plant']} | {row['health_state']}\n"
                f"obs={row['observer_id']} session={row['session_id']}\n"
                f"{row['source']} | {row['license']}"
            )
            draw.multiline_text((x + 5, y + image_height + 4), caption[:220], fill="black", font=_font(12), spacing=2)
        path = output_dir / f"{prefix}_{page_index + 1:02d}.jpg"
        canvas.save(path, quality=92)
        output_paths.append(str(path))
    return output_paths


def all_imported_rows(workspace: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for manifest in sorted((workspace / "imports").glob("*/imported_candidates.csv")):
        rows.extend(read_csv(manifest))
    return rows


def init_workspace(config: dict[str, Any], config_path: Path, workspace: Path) -> dict[str, Any]:
    if (workspace / "workspace_receipt.json").exists():
        raise DatasetPipelineError(f"Workspace is already initialized: {workspace}")
    for directory in ("imports", "reviews", "splits", "status", "templates", "incoming"):
        (workspace / directory).mkdir(parents=True, exist_ok=True)
    for plant in CLASS_NAMES:
        (workspace / "incoming" / plant).mkdir(parents=True, exist_ok=True)
    template_row = {field: "" for field in INTAKE_FIELDS}
    template_row.update(
        {
            "external_id": "unique_source_record_id",
            "file_path": "/absolute/path/to/image.jpg",
            "plant": "marigold",
            "plant_id": "plant_001",
            "observer_id": "observer_001",
            "session_id": "session_2026_10_30_a",
            "source": "mobile_collection",
            "capture_date": "2026-10-30",
            "device": "phone_model",
            "health_state": "healthy",
            "license": "own_photo",
            "source_url": "N/A",
            "license_url": "N/A",
            "attribution": "Photographer name",
            "natural_background": "yes",
            "notes": "",
        }
    )
    write_csv(workspace / "templates" / "intake_metadata_template.csv", INTAKE_FIELDS, [template_row])
    instructions = """# Manual review workflow

1. Import does not approve labels. Complete every metadata field first.
2. Run `review` and inspect every contact sheet.
3. In `manual_review_manifest.csv`, set:
   - species_confirmed: yes/no/uncertain
   - leaf_visible: yes/no
   - image_quality: good/acceptable/reject
   - natural_scene_confirmed: yes/no
   - license_verified: yes/no
   - review_decision: approved/rejected/uncertain
4. Review every `phash_similarity_only_review_required` pair and set a pair decision.
5. `split` fails closed while any approved image has unresolved metadata, label, license, quality, or duplicate status.
6. Never open the protected Locked Test manifest during model development.
"""
    instructions_path = workspace / "templates" / "MANUAL_REVIEW.md"
    instructions_path.write_text(instructions, encoding="utf-8")
    base_config = read_json(Path(config["base_training_config"]))
    pending = json.loads(json.dumps(base_config))
    pending["experiment_name"] = "phytoscan_fresh_b0_natural_data_only_pending"
    pending["data"] = {
        "status": "blocked_until_natural_dataset_split_passes",
        "planned_train_manifest": str(workspace / "splits" / "<split-id>" / "combined_training.csv"),
        "planned_development_manifest": str(workspace / "splits" / "<split-id>" / "development.csv"),
        "locked_test_manifest_intentionally_omitted": True,
    }
    pending["change_control"] = {
        "allowed_change": "data_only",
        "architecture_sha256": canonical_json_hash(base_config["model"]),
        "augmentation_sha256": canonical_json_hash(base_config["augmentation"]),
        "training_performed_by_dataset_pipeline": False,
    }
    write_json(workspace / "pending_fresh_b0_natural_data_only_config.json", pending)
    receipt = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "workspace": str(workspace),
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "classes": list(CLASS_NAMES),
        "targets_total": {
            role: int(value) * len(CLASS_NAMES) for role, value in config["targets_per_class"].items()
        },
        "training_performed": False,
    }
    write_json(workspace / "workspace_receipt.json", receipt)
    return receipt


def import_batch(config: dict[str, Any], workspace: Path, metadata_path: Path, batch_id: str) -> dict[str, Any]:
    batch_dir = workspace / "imports" / safe_id(batch_id)
    if batch_dir.exists():
        raise DatasetPipelineError(f"Import batch already exists: {batch_dir}")
    batch_dir.mkdir(parents=True)
    rows = read_csv(metadata_path)
    if not rows:
        raise DatasetPipelineError("Import metadata is empty")
    missing_columns = [field for field in INTAKE_FIELDS if field not in rows[0]]
    if missing_columns:
        raise DatasetPipelineError(f"Missing metadata columns: {missing_columns}")
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    existing_rows = all_imported_rows(workspace)
    existing_external = {
        (row.get("source", "").strip().lower(), row.get("external_id", "").strip().lower())
        for row in existing_rows
    }
    existing_sha = {row.get("sha256", "").lower() for row in existing_rows if row.get("sha256")}
    seen_external: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        errors = validate_metadata_row(row, config)
        external_key = (row.get("source", "").strip().lower(), row.get("external_id", "").strip().lower())
        if external_key in seen_external:
            errors.append("duplicate_source_external_id_in_batch")
        if external_key in existing_external:
            errors.append("source_external_id_already_imported")
        seen_external.add(external_key)
        source_path = Path(row.get("file_path", ""))
        width, height, decode_error = image_info(source_path) if source_path.is_file() else (0, 0, "file missing")
        if decode_error:
            errors.append("image_decode_failed")
        if width and min(width, height) < int(config["minimum_image_side"]):
            errors.append("image_side_below_minimum")
        if errors:
            rejected.append({"metadata_row": row_number, **row, "rejection_reasons": "|".join(sorted(set(errors)))})
            continue
        sha = sha256_file(source_path)
        if sha in existing_sha:
            rejected.append({"metadata_row": row_number, **row, "rejection_reasons": "sha256_already_imported"})
            continue
        candidate_id = (
            f"{safe_id(row['plant'])}-{sha[:12]}-{safe_id(row['source'])}-{safe_id(row['external_id'])}"
        )
        destination_dir = batch_dir / "images" / row["plant"]
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{candidate_id}{source_path.suffix.lower()}"
        if not destination.exists():
            shutil.copy2(source_path, destination)
        accepted.append(
            {
                "candidate_id": candidate_id,
                "import_batch": batch_dir.name,
                "metadata_row": row_number,
                **row,
                "original_path": str(source_path),
                "staged_path": str(destination),
                "sha256": sha,
                "phash": phash_file(destination),
                "width": width,
                "height": height,
                "semantic_group": semantic_group(row),
                "metadata_valid": "yes",
            }
        )
    imported_fields = list(accepted[0]) if accepted else [
        "candidate_id", "import_batch", "metadata_row", *INTAKE_FIELDS, "original_path", "staged_path",
        "sha256", "phash", "width", "height", "semantic_group", "metadata_valid",
    ]
    rejected_fields = list(rejected[0]) if rejected else ["metadata_row", *INTAKE_FIELDS, "rejection_reasons"]
    write_csv(batch_dir / "imported_candidates.csv", imported_fields, accepted)
    write_csv(batch_dir / "rejected_candidates.csv", rejected_fields, rejected)
    receipt = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "batch_id": batch_dir.name,
        "metadata_path": str(metadata_path),
        "metadata_sha256": sha256_file(metadata_path),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "class_counts": dict(Counter(row["plant"] for row in accepted)),
        "training_performed": False,
    }
    write_json(batch_dir / "import_receipt.json", receipt)
    return receipt


@dataclass(frozen=True)
class Reference:
    path: str
    sha256: str
    phash: str
    role: str


def load_reference_index(config: dict[str, Any]) -> list[Reference]:
    hash_rows = read_csv(Path(config["reference_hash_registry"]))
    phash_rows = read_csv(Path(config["reference_phash_registry"]))
    hashes = {os.path.normcase(row["path"]): row["sha256"].lower() for row in hash_rows}
    phashes = {os.path.normcase(row["path"]): row["phash"].lower() for row in phash_rows}
    role_by_path: dict[str, str] = {}
    for spec in config["reference_manifests"]:
        rows = read_csv(Path(spec["path"]))
        path_column = choose_column(rows, ("path", "image_path", "filepath", "local_path"))
        if not path_column:
            continue
        for row in rows:
            if row.get(path_column):
                role_by_path[os.path.normcase(row[path_column])] = spec["role"]
    paths = sorted(set(hashes) | set(phashes) | set(role_by_path))
    output: list[Reference] = []
    for normalized in paths:
        path = Path(normalized)
        sha, phash = hashes.get(normalized, ""), phashes.get(normalized, "")
        if (not sha or not phash) and path.is_file():
            sha = sha or sha256_file(path)
            phash = phash or phash_file(path)
        if sha and phash:
            output.append(Reference(str(path), sha, phash, role_by_path.get(normalized, "historical_registry")))
    return output


def _pair_row(
    pair_id: str,
    left: dict[str, str],
    right_path: str,
    right_id: str,
    right_sha: str,
    right_phash: str,
    right_group: str,
    right_scope: str,
    right_role: str,
    distance: int,
) -> dict[str, Any]:
    exact = left["sha256"] == right_sha
    same_group = bool(right_group) and left["semantic_group"] == right_group
    if exact:
        classification, decision = "confirmed_exact_duplicate", "true_duplicate"
    elif same_group:
        classification, decision = "source_related_sample", "source_related_sample"
    else:
        classification, decision = "phash_similarity_only_review_required", ""
    return {
        "pair_id": pair_id,
        "left_candidate_id": left["candidate_id"],
        "left_path": left["staged_path"],
        "left_plant": left["plant"],
        "left_sha256": left["sha256"],
        "left_phash": left["phash"],
        "left_semantic_group": left["semantic_group"],
        "right_id": right_id,
        "right_path": right_path,
        "right_sha256": right_sha,
        "right_phash": right_phash,
        "right_semantic_group": right_group,
        "right_scope": right_scope,
        "right_role": right_role,
        "phash_distance": distance,
        "classification": classification,
        "decision": decision,
        "reviewer": "",
        "review_evidence": "",
    }


def build_review(config: dict[str, Any], workspace: Path, review_id: str) -> dict[str, Any]:
    review_dir = workspace / "reviews" / safe_id(review_id)
    if review_dir.exists():
        raise DatasetPipelineError(f"Review directory already exists: {review_dir}")
    review_dir.mkdir(parents=True)
    candidates = all_imported_rows(workspace)
    references = load_reference_index(config) if candidates else []
    reference_phash = np.asarray([int(row.phash, 16) for row in references], dtype=np.uint64)
    limit = int(config["near_duplicate_phash_distance"])
    pair_rows: list[dict[str, Any]] = []
    for left in candidates:
        if reference_phash.size:
            xor = np.bitwise_xor(reference_phash, np.uint64(int(left["phash"], 16)))
            distances = np.bitwise_count(xor) if hasattr(np, "bitwise_count") else np.asarray([int(value).bit_count() for value in xor])
            for ref_index in np.nonzero(distances <= limit)[0]:
                reference = references[int(ref_index)]
                pair_rows.append(
                    _pair_row(
                        f"pair-{len(pair_rows) + 1:06d}", left, reference.path,
                        f"reference-{int(ref_index):06d}", reference.sha256, reference.phash, "",
                        "historical_reference", reference.role, int(distances[int(ref_index)]),
                    )
                )
    for left_index in range(len(candidates) - 1):
        for right_index in range(left_index + 1, len(candidates)):
            left, right = candidates[left_index], candidates[right_index]
            distance = hamming_distance(left["phash"], right["phash"])
            if distance <= limit:
                pair_rows.append(
                    _pair_row(
                        f"pair-{len(pair_rows) + 1:06d}", left, right["staged_path"], right["candidate_id"],
                        right["sha256"], right["phash"], right["semantic_group"], "new_candidate", "new_import", distance,
                    )
                )
    pairs_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pair_rows:
        pairs_by_candidate[pair["left_candidate_id"]].append(pair)
        if pair["right_scope"] == "new_candidate":
            pairs_by_candidate[pair["right_id"]].append(pair)
    review_rows: list[dict[str, Any]] = []
    for row in candidates:
        pairs = pairs_by_candidate.get(row["candidate_id"], [])
        exact_count = sum(pair["classification"] == "confirmed_exact_duplicate" for pair in pairs)
        pending_count = sum(pair["classification"] == "phash_similarity_only_review_required" for pair in pairs)
        review_rows.append(
            {
                **row,
                "exact_duplicate_pair_count": exact_count,
                "phash_review_required_pair_count": pending_count,
                **{field: "" for field in REVIEW_FIELDS},
            }
        )
    review_fields = list(review_rows[0]) if review_rows else [
        "candidate_id", "import_batch", "metadata_row", *INTAKE_FIELDS, "original_path", "staged_path", "sha256",
        "phash", "width", "height", "semantic_group", "metadata_valid", "exact_duplicate_pair_count",
        "phash_review_required_pair_count", *REVIEW_FIELDS,
    ]
    pair_fields = list(pair_rows[0]) if pair_rows else [
        "pair_id", "left_candidate_id", "left_path", "left_plant", "left_sha256", "left_phash",
        "left_semantic_group", "right_id", "right_path", "right_sha256", "right_phash",
        "right_semantic_group", "right_scope", "right_role", "phash_distance", "classification",
        "decision", "reviewer", "review_evidence",
    ]
    review_manifest = review_dir / "manual_review_manifest.csv"
    pair_manifest = review_dir / "duplicate_review_manifest.csv"
    write_csv(review_manifest, review_fields, review_rows)
    write_csv(pair_manifest, pair_fields, pair_rows)
    sheets: list[str] = []
    for plant in CLASS_NAMES:
        plant_rows = [row for row in review_rows if row["plant"] == plant]
        sheets.extend(contact_sheets(plant_rows, review_dir / "contact_sheets", config, plant))
    receipt = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "review_id": review_dir.name,
        "candidates": len(candidates),
        "class_counts": {plant: sum(row["plant"] == plant for row in candidates) for plant in CLASS_NAMES},
        "duplicate_pairs": len(pair_rows),
        "duplicate_classification_counts": dict(Counter(row["classification"] for row in pair_rows)),
        "manual_review_manifest": str(review_manifest),
        "duplicate_review_manifest": str(pair_manifest),
        "contact_sheets": sheets,
        "review_complete": False,
        "training_performed": False,
    }
    write_json(review_dir / "review_receipt.json", receipt)
    return receipt


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
        left, right = self.find(left), self.find(right)
        if left == right:
            return
        if self.rank[left] < self.rank[right]:
            left, right = right, left
        self.parent[right] = left
        if self.rank[left] == self.rank[right]:
            self.rank[left] += 1


def _approved(row: dict[str, str]) -> bool:
    return (
        row.get("species_confirmed", "").strip().lower() == "yes"
        and row.get("leaf_visible", "").strip().lower() == "yes"
        and row.get("image_quality", "").strip().lower() in {"good", "acceptable"}
        and row.get("natural_scene_confirmed", "").strip().lower() == "yes"
        and row.get("license_verified", "").strip().lower() == "yes"
        and row.get("review_decision", "").strip().lower() == "approved"
    )


def coverage_report(config: dict[str, Any], rows: Sequence[dict[str, str]]) -> dict[str, Any]:
    approved = [row for row in rows if _approved(row)]
    total_target = sum(int(value) for value in config["targets_per_class"].values())
    classes: dict[str, Any] = {}
    for plant in CLASS_NAMES:
        plant_rows = [row for row in approved if row["plant"] == plant]
        health = Counter(row["health_state"] for row in plant_rows)
        classes[plant] = {
            "approved_natural_images": len(plant_rows),
            "target_total": total_target,
            "missing_total": max(0, total_target - len(plant_rows)),
            "health_counts": dict(health),
            "health_missing": {
                state: max(0, int(target) - health[state])
                for state, target in config["health_targets_per_class"].items()
            },
            "observer_groups": len({semantic_keys(row)[0] for row in plant_rows}),
            "session_groups": len({semantic_keys(row)[1] for row in plant_rows}),
            "plant_groups": len({semantic_keys(row)[2] for row in plant_rows}),
        }
    all_classes_ready = all(
        value["missing_total"] == 0 and all(missing == 0 for missing in value["health_missing"].values())
        for value in classes.values()
    )
    return {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "targets": config["targets_per_class"],
        "target_totals": {role: int(value) * len(CLASS_NAMES) for role, value in config["targets_per_class"].items()},
        "approved_total": len(approved),
        "classes": classes,
        "ready_for_group_split": all_classes_ready,
        "training_performed": False,
    }


def _select_components(
    components: list[dict[str, Any]], targets: dict[str, int], seed: int
) -> tuple[set[int], dict[str, int]]:
    selected: set[int] = set()
    counts = Counter()
    remaining = list(components)
    while any(counts[plant] < targets[plant] for plant in CLASS_NAMES):
        deficits = {plant: max(0, targets[plant] - counts[plant]) for plant in CLASS_NAMES}
        scored: list[tuple[float, int, int, str, dict[str, Any]]] = []
        for component in remaining:
            coverage = sum(min(deficits[plant], component["class_counts"].get(plant, 0)) for plant in CLASS_NAMES)
            if coverage == 0:
                continue
            size = len(component["indexes"])
            tie = hashlib.sha256(f"{seed}|{component['id']}".encode()).hexdigest()
            scored.append((coverage / size, coverage, -size, tie, component))
        if not scored:
            break
        chosen = max(scored, key=lambda item: item[:4])[4]
        selected.add(chosen["root"])
        counts.update(chosen["class_counts"])
        remaining.remove(chosen)
    return selected, {plant: counts[plant] for plant in CLASS_NAMES}


def _normalized_new_row(row: dict[str, str], split: str) -> dict[str, Any]:
    return {
        "path": row["staged_path"],
        "plant": row["plant"],
        "label": CLASS_NAMES.index(row["plant"]),
        "source": row["source"],
        "group_id": row["component_id"],
        "sha256": row["sha256"],
        "phash": row["phash"],
        "split": split,
        "plant_id": row["plant_id"],
        "observer_id": row["observer_id"],
        "session_id": row["session_id"],
        "capture_date": row["capture_date"],
        "device": row["device"],
        "health_state": row["health_state"],
        "license": row["license"],
        "source_url": row["source_url"],
        "license_url": row["license_url"],
        "attribution": row["attribution"],
        "natural_background": row["natural_background"],
        "review_status": "approved",
        "leaf_visible": "yes",
        "correct_plant": "yes",
        "image_quality": row["image_quality"],
        "target_plant_visible": "yes",
        "single_clear_target": "yes",
        "leaf_sufficient": "yes",
        "data_origin": "natural_expansion_v1",
    }


def _base_training_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = read_csv(Path(config["base_training_manifest"]))
    path_column = choose_column(rows, ("path", "image_path", "filepath"))
    plant_column = choose_column(rows, ("plant", "plant_code"))
    source_column = choose_column(rows, ("source", "v3_source"))
    group_column = choose_column(rows, ("group_id", "source_group", "duplicate_group"))
    sha_column = choose_column(rows, ("sha256", "sha"))
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        plant = row[plant_column] if plant_column else ""
        output.append(
            {
                "path": row[path_column] if path_column else "",
                "plant": plant,
                "label": CLASS_NAMES.index(plant),
                "source": row.get(source_column, "existing_v5_training") if source_column else "existing_v5_training",
                "group_id": row.get(group_column, f"existing_row_{index}") if group_column else f"existing_row_{index}",
                "sha256": row.get(sha_column, "") if sha_column else "",
                "phash": row.get("phash", ""),
                "split": "training",
                "plant_id": "historical_not_available",
                "observer_id": "historical_not_available",
                "session_id": "historical_not_available",
                "capture_date": "historical_not_available",
                "device": "historical_not_available",
                "health_state": "historical_not_available",
                "license": "historical_governance",
                "source_url": "historical_governance",
                "license_url": "historical_governance",
                "attribution": "historical_governance",
                "natural_background": "mixed_historical",
                "review_status": "historical_audited_pool",
                "leaf_visible": "historical_audited_pool",
                "correct_plant": "historical_audited_pool",
                "image_quality": "historical_audited_pool",
                "target_plant_visible": "historical_audited_pool",
                "single_clear_target": "historical_audited_pool",
                "leaf_sufficient": "historical_audited_pool",
                "data_origin": "existing_v5_training",
            }
        )
    return output


def split_reviewed(
    config: dict[str, Any], workspace: Path, review_manifest: Path, duplicate_manifest: Path, split_id: str
) -> dict[str, Any]:
    split_dir = workspace / "splits" / safe_id(split_id)
    if split_dir.exists():
        raise DatasetPipelineError(f"Split directory already exists: {split_dir}")
    split_dir.mkdir(parents=True)
    all_rows = read_csv(review_manifest)
    pairs = read_csv(duplicate_manifest)
    coverage = coverage_report(config, all_rows)
    write_json(split_dir / "coverage_report.json", coverage)
    unresolved_pairs = [
        row for row in pairs
        if row["classification"] == "phash_similarity_only_review_required"
        and row.get("decision", "").strip() not in PAIR_DECISIONS
    ]
    approved_rows = [row for row in all_rows if _approved(row)]
    blocking = []
    if not coverage["ready_for_group_split"]:
        blocking.append("insufficient_approved_images_for_50_20_20_per_class")
    if unresolved_pairs:
        blocking.append("unresolved_phash_pairs")
    if blocking:
        report = {
            "schema_version": 1,
            "created_at_utc": utc_now(),
            "passed": False,
            "decision": "split_blocked_fail_closed",
            "blocking_reasons": blocking,
            "approved_images": len(approved_rows),
            "unresolved_phash_pairs": len(unresolved_pairs),
            "locked_test_manifest_created": False,
            "training_config_created": False,
            "training_performed": False,
        }
        write_json(split_dir / "split_report.json", report)
        return report
    index_by_id = {row["candidate_id"]: index for index, row in enumerate(approved_rows)}
    union = UnionFind(len(approved_rows))
    by_semantic: dict[str, int] = {}
    for index, row in enumerate(approved_rows):
        for key in semantic_keys(row):
            if key in by_semantic:
                union.union(index, by_semantic[key])
            else:
                by_semantic[key] = index
    excluded: set[int] = set()
    allowed_false_pairs: set[frozenset[str]] = set()
    for pair in pairs:
        left_index = index_by_id.get(pair["left_candidate_id"])
        right_index = index_by_id.get(pair["right_id"]) if pair["right_scope"] == "new_candidate" else None
        decision = pair.get("decision", "").strip()
        if pair["classification"] == "confirmed_exact_duplicate" or decision == "true_duplicate":
            if pair["right_scope"] == "historical_reference":
                if left_index is not None:
                    excluded.add(left_index)
            elif left_index is not None and right_index is not None:
                union.union(left_index, right_index)
                excluded.add(max(left_index, right_index))
        elif decision == "source_related_sample" and left_index is not None and right_index is not None:
            union.union(left_index, right_index)
        elif decision in {"uncertain", "label_issue"}:
            if left_index is not None:
                excluded.add(left_index)
            if right_index is not None:
                excluded.add(right_index)
        elif decision == "false_phash_collision":
            allowed_false_pairs.add(frozenset((pair["left_candidate_id"], pair["right_id"])))
    eligible_indexes = [index for index in range(len(approved_rows)) if index not in excluded]
    components_by_root: dict[int, list[int]] = defaultdict(list)
    for index in eligible_indexes:
        components_by_root[union.find(index)].append(index)
    components: list[dict[str, Any]] = []
    for number, (root, indexes) in enumerate(sorted(components_by_root.items()), start=1):
        component_id = f"natural_group_{number:05d}"
        for index in indexes:
            approved_rows[index]["component_id"] = component_id
        components.append(
            {
                "root": root,
                "id": component_id,
                "indexes": indexes,
                "class_counts": Counter(approved_rows[index]["plant"] for index in indexes),
            }
        )
    locked_targets = {plant: int(config["targets_per_class"]["locked_test"]) for plant in CLASS_NAMES}
    locked_roots, locked_counts = _select_components(components, locked_targets, int(config["seed"]) + 1)
    remaining = [component for component in components if component["root"] not in locked_roots]
    dev_targets = {plant: int(config["targets_per_class"]["development"]) for plant in CLASS_NAMES}
    dev_roots, dev_counts = _select_components(remaining, dev_targets, int(config["seed"]) + 2)
    train_roots = {component["root"] for component in remaining if component["root"] not in dev_roots}
    split_by_root = {**{root: "locked_test" for root in locked_roots}, **{root: "development" for root in dev_roots}, **{root: "training" for root in train_roots}}
    split_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index in eligible_indexes:
        split_name = split_by_root[union.find(index)]
        split_rows[split_name].append(_normalized_new_row(approved_rows[index], split_name))
    counts = {
        split: {plant: sum(row["plant"] == plant for row in split_rows[split]) for plant in CLASS_NAMES}
        for split in ("training", "development", "locked_test")
    }
    targets = config["targets_per_class"]
    count_passed = all(counts[split][plant] >= int(targets[split]) for split in targets for plant in CLASS_NAMES)
    groups = {
        split: {row["group_id"] for row in split_rows[split]}
        for split in ("training", "development", "locked_test")
    }
    shas = {
        split: {row["sha256"] for row in split_rows[split]}
        for split in ("training", "development", "locked_test")
    }
    group_overlap = sum(len(groups[left] & groups[right]) for left, right in (("training", "development"), ("training", "locked_test"), ("development", "locked_test")))
    sha_overlap = sum(len(shas[left] & shas[right]) for left, right in (("training", "development"), ("training", "locked_test"), ("development", "locked_test")))
    split_by_candidate = {
        approved_rows[index]["candidate_id"]: split_by_root[union.find(index)]
        for index in eligible_indexes
    }
    phash_cross_split_total = 0
    phash_cross_split_false_collisions = 0
    phash_cross_split_unresolved: list[str] = []
    for pair in pairs:
        if pair["right_scope"] != "new_candidate":
            continue
        left_split = split_by_candidate.get(pair["left_candidate_id"])
        right_split = split_by_candidate.get(pair["right_id"])
        if not left_split or not right_split or left_split == right_split:
            continue
        phash_cross_split_total += 1
        if pair.get("decision", "").strip() == "false_phash_collision":
            phash_cross_split_false_collisions += 1
        else:
            phash_cross_split_unresolved.append(pair["pair_id"])
    if not count_passed or group_overlap or sha_overlap or phash_cross_split_unresolved:
        report = {
            "schema_version": 1,
            "created_at_utc": utc_now(),
            "passed": False,
            "decision": "split_blocked_fail_closed",
            "blocking_reasons": [
                *([] if count_passed else ["group_allocation_cannot_meet_per_class_targets"]),
                *([] if group_overlap == 0 else ["semantic_group_overlap"]),
                *([] if sha_overlap == 0 else ["sha256_overlap"]),
                *([] if not phash_cross_split_unresolved else ["unresolved_cross_split_phash_candidates"]),
            ],
            "counts": counts,
            "group_overlap_count": group_overlap,
            "sha256_overlap_count": sha_overlap,
            "phash_cross_split_candidate_count": phash_cross_split_total,
            "phash_cross_split_false_collision_count": phash_cross_split_false_collisions,
            "phash_cross_split_unresolved_pair_ids": phash_cross_split_unresolved,
            "locked_test_manifest_created": False,
            "training_config_created": False,
            "training_performed": False,
        }
        write_json(split_dir / "split_report.json", report)
        return report
    fields = list(split_rows["training"][0])
    natural_train = split_dir / "natural_training.csv"
    development = split_dir / "development.csv"
    protected_dir = split_dir / "protected_locked_test"
    locked = protected_dir / "locked_test_manifest.csv"
    write_csv(natural_train, fields, split_rows["training"])
    write_csv(development, fields, split_rows["development"])
    write_csv(locked, fields, split_rows["locked_test"])
    combined_rows = _base_training_rows(config) + split_rows["training"]
    combined = split_dir / "combined_training.csv"
    write_csv(combined, fields, combined_rows)
    duplicate_receipt_path = split_dir / "duplicate_leakage_receipt.json"
    duplicate_receipt = {
        "schema_version": 1,
        "passed": True,
        "near_duplicate_review_complete": True,
        "train_manifest_sha256": sha256_file(combined),
        "development_manifest_sha256": sha256_file(development),
        "locked_test_manifest_sha256": sha256_file(locked),
        "group_overlap_count": group_overlap,
        "sha256_overlap_count": sha_overlap,
        "phash_threshold": int(config["near_duplicate_phash_distance"]),
        "false_collision_pairs": len(allowed_false_pairs),
        "phash_cross_split_candidate_count": phash_cross_split_total,
        "phash_cross_split_false_collision_count": phash_cross_split_false_collisions,
        "phash_cross_split_unresolved_count": 0,
        "notes": [
            "Locked Test is excluded from training configuration and model selection.",
            "pHash similarity alone was not treated as proof of duplication.",
        ],
    }
    write_json(duplicate_receipt_path, duplicate_receipt)
    locked_receipt = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "manifest_sha256": sha256_file(locked),
        "counts": counts["locked_test"],
        "policy": "Open once only after model/config freeze for final evaluation; never use for model or hyperparameter selection.",
    }
    write_json(protected_dir / "locked_test_receipt.json", locked_receipt)
    warning = protected_dir / "LOCKED_TEST_DO_NOT_OPEN_DURING_DEVELOPMENT.txt"
    warning.write_text(locked_receipt["policy"] + "\n", encoding="utf-8")
    for protected in (locked, protected_dir / "locked_test_receipt.json", warning):
        protected.chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    base_config = read_json(Path(config["base_training_config"]))
    training_config = json.loads(json.dumps(base_config))
    training_config["experiment_name"] = "phytoscan_fresh_b0_natural_data_only"
    training_config["data"]["train_manifest"] = str(combined)
    training_config["data"]["development_manifest"] = str(development)
    training_config["data"]["train"].update({
        "status": "audited_v5_training_manifest", "path_column": "path", "label_column": "plant",
        "source_column": "source", "group_column": "group_id", "sha_column": "sha256",
    })
    training_config["data"]["development"] = {
        "status": "eligible_group_disjoint_development",
        "duplicate_audit_status": "passed_path_sha_group_and_near_duplicate_review",
        "duplicate_audit_receipt": str(duplicate_receipt_path),
        "path_column": "path", "label_column": "plant", "source_column": "source",
        "group_column": "group_id", "sha_column": "sha256", "min_samples_per_class": 20,
        "required_manifest_flags": {
            "review_status": ["approved"], "leaf_visible": ["yes"], "correct_plant": ["yes"],
            "image_quality": ["good", "acceptable"],
        },
        "quality_review_manifest": str(development),
        "quality_path_column": "path",
        "required_quality_flags": {
            "target_plant_visible": ["yes"], "single_clear_target": ["yes"], "leaf_sufficient": ["yes"],
        },
    }
    training_config["change_control"] = {
        "allowed_change": "data_only",
        "base_config": config["base_training_config"],
        "architecture_unchanged": training_config["model"] == base_config["model"],
        "augmentation_unchanged": training_config["augmentation"] == base_config["augmentation"],
        "locked_test_path_in_config": False,
        "training_performed_by_dataset_pipeline": False,
    }
    config_path = split_dir / "fresh_b0_natural_data_only.ready.json"
    write_json(config_path, training_config)
    report = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "passed": True,
        "decision": "dataset_ready_training_not_started",
        "counts": counts,
        "group_overlap_count": group_overlap,
        "sha256_overlap_count": sha_overlap,
        "phash_cross_split_candidate_count": phash_cross_split_total,
        "phash_cross_split_false_collision_count": phash_cross_split_false_collisions,
        "manifests": {
            "combined_training": {"path": str(combined), "sha256": sha256_file(combined)},
            "development": {"path": str(development), "sha256": sha256_file(development)},
            "locked_test": {"protected": True, "sha256": sha256_file(locked)},
        },
        "training_config": str(config_path),
        "locked_test_manifest_created": True,
        "training_config_created": True,
        "training_performed": False,
    }
    write_json(split_dir / "split_report.json", report)
    return report


def status_command(config: dict[str, Any], workspace: Path, review_manifest: Path | None, status_id: str) -> dict[str, Any]:
    status_dir = workspace / "status" / safe_id(status_id)
    if status_dir.exists():
        raise DatasetPipelineError(f"Status directory already exists: {status_dir}")
    status_dir.mkdir(parents=True)
    rows = read_csv(review_manifest) if review_manifest else []
    report = coverage_report(config, rows)
    report.update(
        {
            "review_manifest": str(review_manifest) if review_manifest else None,
            "imported_candidates": len(all_imported_rows(workspace)),
            "locked_test_accessed": False,
            "next_action": (
                "run group-aware split after duplicate review" if report["ready_for_group_split"]
                else "collect/import/review the reported missing natural images"
            ),
        }
    )
    write_json(status_dir / "dataset_coverage_report.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PhytoScan natural-image dataset import and split pipeline")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    import_parser = sub.add_parser("import")
    import_parser.add_argument("--metadata", type=Path, required=True)
    import_parser.add_argument("--batch-id", required=True)
    review_parser = sub.add_parser("review")
    review_parser.add_argument("--review-id", required=True)
    split_parser = sub.add_parser("split")
    split_parser.add_argument("--review-manifest", type=Path, required=True)
    split_parser.add_argument("--duplicate-manifest", type=Path, required=True)
    split_parser.add_argument("--split-id", required=True)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--review-manifest", type=Path)
    status_parser.add_argument("--status-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = read_json(args.config)
    if tuple(config["classes"]) != CLASS_NAMES:
        raise DatasetPipelineError("Class order differs from the locked six-class order")
    if args.command == "init":
        result = init_workspace(config, args.config, args.workspace)
    else:
        if not (args.workspace / "workspace_receipt.json").is_file():
            raise DatasetPipelineError("Run init before this command")
        if args.command == "import":
            result = import_batch(config, args.workspace, args.metadata, args.batch_id)
        elif args.command == "review":
            result = build_review(config, args.workspace, args.review_id)
        elif args.command == "split":
            result = split_reviewed(
                config, args.workspace, args.review_manifest, args.duplicate_manifest, args.split_id
            )
        else:
            result = status_command(config, args.workspace, args.review_manifest, args.status_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "split" and result.get("passed") is False:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
