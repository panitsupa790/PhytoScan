from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


CLASS_NAMES = (
    "chrysanthemum",
    "marigold",
    "money_plant",
    "rose",
    "snake_plant",
    "spider_plant",
)

PATH_COLUMNS = ("path", "image_path", "filepath", "file_path", "local_path")
LABEL_COLUMNS = ("plant", "plant_code", "label", "class_name", "class")
SOURCE_COLUMNS = ("source", "v3_source", "source_type", "dataset_source", "domain", "source_group")
GROUP_COLUMNS = ("group_id", "v3_group", "source_group", "plant_id", "observation_id", "session_id")
SHA_COLUMNS = ("sha256", "image_sha256", "file_sha256")


class FastTrackError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImageRecord:
    path: Path
    label: str
    class_index: int
    source: str
    group_id: str | None
    sha256: str | None
    row_number: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FastTrackError(f"Cannot read JSON {path}: {exc}") from exc


def canonical_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise FastTrackError(f"Cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except OSError as exc:
        raise FastTrackError(f"Cannot read CSV {path}: {exc}") from exc


def write_json(path: Path, value: Any, *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FastTrackError(f"Refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    if path.exists():
        raise FastTrackError(f"Refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def choose_column(rows: Sequence[dict[str, str]], configured: str | None, candidates: Sequence[str]) -> str:
    if not rows:
        raise FastTrackError("Manifest has no rows")
    columns = set(rows[0])
    if configured:
        if configured not in columns:
            raise FastTrackError(f"Configured column {configured!r} is missing; found {sorted(columns)}")
        return configured
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise FastTrackError(f"None of the expected columns {list(candidates)} exist; found {sorted(columns)}")


def _resolve_image_path(raw_path: str, manifest_path: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    # Lexical normalization avoids thousands of slow realpath/stat calls on
    # WSL DrvFS. File existence is checked explicitly where required.
    return Path(os.path.abspath(path))


def records_from_manifest(
    manifest_path: Path,
    settings: dict[str, Any],
    *,
    require_files: bool,
) -> tuple[list[ImageRecord], dict[str, str]]:
    rows = read_csv(manifest_path)
    split_column = settings.get("split_column")
    split_value = settings.get("split_value")
    if split_column and split_value is not None:
        if split_column not in rows[0]:
            raise FastTrackError(f"Split column {split_column!r} is missing from {manifest_path}")
        rows = [row for row in rows if row.get(split_column) == str(split_value)]
    if not rows:
        raise FastTrackError(f"No rows selected from {manifest_path}")

    path_column = choose_column(rows, settings.get("path_column"), PATH_COLUMNS)
    label_column = choose_column(rows, settings.get("label_column"), LABEL_COLUMNS)
    source_column = choose_column(rows, settings.get("source_column"), SOURCE_COLUMNS)
    group_column = next((name for name in ([settings.get("group_column")] if settings.get("group_column") else GROUP_COLUMNS) if name and name in rows[0]), None)
    sha_column = next((name for name in ([settings.get("sha_column")] if settings.get("sha_column") else SHA_COLUMNS) if name and name in rows[0]), None)

    records: list[ImageRecord] = []
    missing: list[str] = []
    for row_number, row in enumerate(rows, start=2):
        label = row.get(label_column, "").strip()
        if label not in CLASS_NAMES:
            raise FastTrackError(f"Unexpected class {label!r} at {manifest_path}:{row_number}")
        path = _resolve_image_path(row.get(path_column, ""), manifest_path)
        if require_files and not path.is_file():
            missing.append(str(path))
        records.append(
            ImageRecord(
                path=path,
                label=label,
                class_index=CLASS_NAMES.index(label),
                source=(row.get(source_column) or "unknown").strip() or "unknown",
                group_id=(row.get(group_column) or "").strip() or None if group_column else None,
                sha256=(row.get(sha_column) or "").strip().lower() or None if sha_column else None,
                row_number=row_number,
            )
        )
    if missing:
        preview = ", ".join(missing[:5])
        raise FastTrackError(f"{len(missing)} image files are missing; first paths: {preview}")
    return records, {
        "path": path_column,
        "label": label_column,
        "source": source_column,
        "group": group_column or "",
        "sha256": sha_column or "",
    }


def class_counts(records: Sequence[ImageRecord]) -> dict[str, int]:
    counts = Counter(record.label for record in records)
    return {name: int(counts.get(name, 0)) for name in CLASS_NAMES}


def source_counts(records: Sequence[ImageRecord]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        counts[record.label][record.source] += 1
    return {name: dict(sorted(counts[name].items())) for name in CLASS_NAMES}


def _normalized_paths(records: Sequence[ImageRecord]) -> set[str]:
    return {os.path.normcase(str(record.path)) for record in records}


def overlap_summary(train: Sequence[ImageRecord], validation: Sequence[ImageRecord]) -> dict[str, Any]:
    path_overlap = sorted(_normalized_paths(train) & _normalized_paths(validation))
    train_sha = {record.sha256 for record in train if record.sha256}
    validation_sha = {record.sha256 for record in validation if record.sha256}
    train_groups = {record.group_id for record in train if record.group_id}
    validation_groups = {record.group_id for record in validation if record.group_id}
    return {
        "path_count": len(path_overlap),
        "path_examples": path_overlap[:10],
        "sha256_count": len(train_sha & validation_sha),
        "sha256_available": bool(train_sha and validation_sha),
        "group_count": len(train_groups & validation_groups),
        "group_available": bool(train_groups and validation_groups),
    }


def _quality_review_check(development_records: Sequence[ImageRecord], config: dict[str, Any]) -> dict[str, Any]:
    quality_path_value = config.get("quality_review_manifest")
    if not quality_path_value:
        return {"passed": False, "reason": "quality_review_manifest is required"}
    quality_path = Path(quality_path_value)
    rows = read_csv(quality_path)
    if not rows:
        return {"passed": False, "reason": "quality review manifest is empty"}
    path_column = choose_column(rows, config.get("quality_path_column"), PATH_COLUMNS)
    reviewed_by_path = {
        os.path.normcase(str(_resolve_image_path(row[path_column], quality_path))): row for row in rows
    }
    required_flags: dict[str, list[str]] = config.get("required_quality_flags", {})
    invalid: list[dict[str, Any]] = []
    missing = 0
    for record in development_records:
        row = reviewed_by_path.get(os.path.normcase(str(record.path)))
        if row is None:
            missing += 1
            continue
        bad_flags = {
            name: row.get(name)
            for name, accepted in required_flags.items()
            if str(row.get(name, "")).strip().lower() not in {str(value).lower() for value in accepted}
        }
        if bad_flags:
            invalid.append({"path": str(record.path), "invalid_flags": bad_flags})
    return {
        "passed": missing == 0 and not invalid,
        "reviewed": len(development_records) - missing,
        "missing_reviews": missing,
        "invalid_count": len(invalid),
        "invalid_examples": invalid[:10],
        "manifest": str(quality_path),
        "manifest_sha256": sha256_file(quality_path),
    }


def _manifest_flags_check(manifest_path: Path, settings: dict[str, Any]) -> dict[str, Any]:
    required_flags: dict[str, list[str]] = settings.get("required_manifest_flags", {})
    if not required_flags:
        return {"passed": False, "reason": "required_manifest_flags is required"}
    rows = read_csv(manifest_path)
    split_column = settings.get("split_column")
    split_value = settings.get("split_value")
    if split_column and split_value is not None:
        rows = [row for row in rows if row.get(split_column) == str(split_value)]
    invalid: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        bad = {
            name: row.get(name)
            for name, accepted in required_flags.items()
            if str(row.get(name, "")).strip().lower() not in {str(value).lower() for value in accepted}
        }
        if bad:
            invalid.append({"row": row_number, "invalid_flags": bad})
    return {
        "passed": bool(rows) and not invalid,
        "rows_checked": len(rows),
        "invalid_count": len(invalid),
        "invalid_examples": invalid[:10],
    }


def _duplicate_audit_check(
    settings: dict[str, Any], train_manifest_sha256: str, development_manifest_sha256: str
) -> dict[str, Any]:
    receipt_value = settings.get("duplicate_audit_receipt")
    if not receipt_value:
        return {"passed": False, "reason": "duplicate_audit_receipt is required"}
    receipt_path = Path(receipt_value)
    receipt = load_json(receipt_path)
    passed = (
        receipt.get("passed") is True
        and receipt.get("near_duplicate_review_complete") is True
        and receipt.get("train_manifest_sha256") == train_manifest_sha256
        and receipt.get("development_manifest_sha256") == development_manifest_sha256
    )
    return {
        "passed": passed,
        "receipt": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "declared_passed": receipt.get("passed"),
        "near_duplicate_review_complete": receipt.get("near_duplicate_review_complete"),
        "train_manifest_hash_matches": receipt.get("train_manifest_sha256") == train_manifest_sha256,
        "development_manifest_hash_matches": receipt.get("development_manifest_sha256")
        == development_manifest_sha256,
        "notes": receipt.get("notes", []),
    }


def run_preflight(config: dict[str, Any], *, require_files: bool = True) -> tuple[dict[str, Any], list[ImageRecord], list[ImageRecord]]:
    data = config["data"]
    train_path = Path(data["train_manifest"])
    development_path = Path(data["development_manifest"])
    development_is_eligible = data["development"].get("status") == "eligible_group_disjoint_development"
    train_records, train_columns = records_from_manifest(
        train_path,
        data["train"],
        require_files=require_files and development_is_eligible,
    )
    development_records, development_columns = records_from_manifest(
        development_path, data["development"], require_files=require_files
    )
    train_manifest_sha256 = sha256_file(train_path)
    development_manifest_sha256 = sha256_file(development_path)
    counts = class_counts(development_records)
    minimum = int(data["development"]["min_samples_per_class"])
    class_coverage_passed = all(counts[name] >= minimum for name in CLASS_NAMES)
    status = data["development"].get("status", "unspecified")
    status_passed = status == "eligible_group_disjoint_development"
    overlap = overlap_summary(train_records, development_records)
    overlap_passed = (
        overlap["path_count"] == 0
        and (not overlap["sha256_available"] or overlap["sha256_count"] == 0)
        and (not overlap["group_available"] or overlap["group_count"] == 0)
    )
    quality = _quality_review_check(development_records, data["development"])
    manual_review = _manifest_flags_check(development_path, data["development"])
    duplicate_audit = _duplicate_audit_check(
        data["development"], train_manifest_sha256, development_manifest_sha256
    )
    checks = {
        "train_manifest_status_is_audited": data["train"].get("status") == "audited_v5_training_manifest",
        "development_status_is_eligible": status_passed,
        "duplicate_audit_status_is_eligible": (
            data["development"].get("duplicate_audit_status")
            == "passed_path_sha_group_and_near_duplicate_review"
            and duplicate_audit["passed"]
        ),
        "all_six_classes_meet_minimum": class_coverage_passed,
        "manual_review_passed": bool(manual_review["passed"]),
        "quality_review_passed": bool(quality["passed"]),
        "no_train_development_overlap": overlap_passed,
        "class_order_exact": tuple(config["classes"]) == CLASS_NAMES,
        "legacy_or_locked_test_configured": any("test" in key.lower() for key in data),
    }
    passed = (
        all(value for key, value in checks.items() if key != "legacy_or_locked_test_configured")
        and not checks["legacy_or_locked_test_configured"]
    )
    report = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "passed": passed,
        "decision": "training_allowed" if passed else "training_blocked_fail_closed",
        "checks": checks,
        "blocking_reasons": [key for key, value in checks.items() if (key == "legacy_or_locked_test_configured" and value) or (key != "legacy_or_locked_test_configured" and not value)],
        "development_status": status,
        "minimum_samples_per_class": minimum,
        "train_samples": len(train_records),
        "development_samples": len(development_records),
        "development_class_counts": counts,
        "train_class_counts": class_counts(train_records),
        "train_source_counts": source_counts(train_records),
        "overlap": overlap,
        "quality_review": quality,
        "manual_review": manual_review,
        "duplicate_audit": duplicate_audit,
        "columns": {"train": train_columns, "development": development_columns},
        "artifacts": {
            "train_manifest": str(train_path),
            "train_manifest_sha256": train_manifest_sha256,
            "development_manifest": str(development_path),
            "development_manifest_sha256": development_manifest_sha256,
        },
        "policy": {
            "legacy_test_used_for_selection": False,
            "locked_test_used_for_selection": False,
            "overused_external_development_may_select_checkpoint": False,
        },
    }
    return report, train_records, development_records


def build_balanced_schedule(
    records: Sequence[ImageRecord],
    *,
    seed: int,
    max_repeats_per_image: int,
) -> tuple[list[ImageRecord], dict[str, Any]]:
    """Build a class/source-aware epoch without repeating an image above the cap.

    Each class targets min(largest class, smallest class * repeat cap). Within a
    class, inverse-square-root source weighting gives minority sources a modest
    boost while sampling from a finite repeated pool without replacement.
    """
    if max_repeats_per_image < 1:
        raise FastTrackError("max_repeats_per_image must be >= 1")
    by_class: dict[str, list[ImageRecord]] = {name: [] for name in CLASS_NAMES}
    for record in records:
        by_class[record.label].append(record)
    if any(not by_class[name] for name in CLASS_NAMES):
        raise FastTrackError("Training manifest must contain all six classes")
    sizes = [len(by_class[name]) for name in CLASS_NAMES]
    target = min(max(sizes), min(sizes) * max_repeats_per_image)
    rng = np.random.default_rng(seed)
    scheduled: list[ImageRecord] = []
    repeat_counter: Counter[tuple[str, int]] = Counter()
    for class_name in CLASS_NAMES:
        class_records = by_class[class_name]
        source_size = Counter(record.source for record in class_records)
        candidate_records: list[ImageRecord] = []
        weights: list[float] = []
        for record in class_records:
            for _ in range(max_repeats_per_image):
                candidate_records.append(record)
                weights.append(1.0 / math.sqrt(source_size[record.source]))
        take = min(target, len(candidate_records))
        probabilities = np.asarray(weights, dtype=np.float64)
        probabilities /= probabilities.sum()
        selected = rng.choice(len(candidate_records), size=take, replace=False, p=probabilities)
        for index in selected:
            record = candidate_records[int(index)]
            scheduled.append(record)
            repeat_counter[(str(record.path), record.row_number)] += 1
    rng.shuffle(scheduled)
    repeats = Counter(repeat_counter.values())
    receipt = {
        "strategy": "class_target_with_inverse_sqrt_source_weight_finite_pool",
        "seed": seed,
        "input_samples": len(records),
        "epoch_samples": len(scheduled),
        "target_per_class": target,
        "max_repeats_per_image": max_repeats_per_image,
        "observed_max_repeats": max(repeat_counter.values(), default=0),
        "repeat_histogram": {str(key): int(value) for key, value in sorted(repeats.items())},
        "scheduled_class_counts": class_counts(scheduled),
        "scheduled_source_counts": source_counts(scheduled),
    }
    return scheduled, receipt


def configure_reproducibility(seed: int) -> None:
    os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
    random.seed(seed)
    np.random.seed(seed)
    try:
        import tensorflow as tf

        tf.keras.utils.set_random_seed(seed)
        tf.config.experimental.enable_op_determinism()
    except (ImportError, RuntimeError):
        pass
