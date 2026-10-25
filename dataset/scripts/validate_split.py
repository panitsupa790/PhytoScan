from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from build_clean_dataset import BuildError, CLASSES, load_and_plan
from split_dataset import (
    DEFAULT_SEED,
    SPLITS,
    SPLIT_MANIFEST_FIELDS,
    assignment_digest,
    build_summary,
    cleaned_fingerprint,
    generate_assignments,
    read_csv,
    safe_relative_path,
    validate_assignments,
    validate_cleaned_prerequisites,
)
from validate_dataset import SUPPORTED_EXTENSIONS, validate_image


SPLIT_VALIDATION_FIELDS = (
    "split",
    "class",
    "filename",
    "extension",
    "width",
    "height",
    "mode",
    "sha256",
    "status",
    "error",
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def write_validation(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SPLIT_VALIDATION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def scan_split(split_root: Path) -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    errors: list[str] = []
    if not split_root.is_dir():
        return rows, [f"Missing split root: {split_root}"]

    unknown_split_dirs = sorted(
        path.name
        for path in split_root.iterdir()
        if path.is_dir() and path.name not in SPLITS
    )
    if unknown_split_dirs:
        errors.append(f"Unknown split directories: {', '.join(unknown_split_dirs)}")
    root_files = sorted(
        path.name
        for path in split_root.iterdir()
        if path.is_file() and path.name != ".gitkeep"
    )
    if root_files:
        errors.append(f"Files found at split root: {', '.join(root_files[:5])}")

    for split_name in SPLITS:
        split_dir = split_root / split_name
        if not split_dir.is_dir():
            errors.append(f"Missing split directory: {split_name}")
            continue
        unknown_classes = sorted(
            path.name
            for path in split_dir.iterdir()
            if path.is_dir() and path.name not in CLASSES
        )
        if unknown_classes:
            errors.append(
                f"Unknown classes under {split_name}: {', '.join(unknown_classes)}"
            )
        split_root_files = sorted(
            path.name
            for path in split_dir.iterdir()
            if path.is_file() and path.name != ".gitkeep"
        )
        if split_root_files:
            errors.append(
                f"Files found directly under {split_name}: {', '.join(split_root_files[:5])}"
            )
        for class_name in CLASSES:
            class_dir = split_dir / class_name
            if not class_dir.is_dir():
                errors.append(f"Missing split class directory: {split_name}/{class_name}")
                continue
            files = sorted(
                (
                    path
                    for path in class_dir.rglob("*")
                    if path.is_file() and path.name != ".gitkeep"
                ),
                key=lambda path: (
                    path.relative_to(class_dir).as_posix().casefold(),
                    path.relative_to(class_dir).as_posix(),
                ),
            )
            for path in files:
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    errors.append(
                        f"Unsupported split file: {split_name}/{class_name}/{path.name}"
                    )
                image_row = validate_image(path, class_name, class_dir)
                rows.append({"split": split_name, **image_row})
    return rows, errors


def compare_summary(
    summary: dict[str, object], expected: dict[str, object]
) -> list[str]:
    fields = (
        "seed",
        "ratios",
        "allocation_method",
        "cleaned_fingerprint_before_split",
        "total",
        "counts_per_class",
        "counts_per_split",
        "actual_percentages",
        "assignment_sha256",
        "policies",
    )
    return [
        f"Split summary differs from current assignment: {field}"
        for field in fields
        if summary.get(field) != expected.get(field)
    ]


def validate_split() -> tuple[bool, dict[str, object]]:
    root = project_root()
    dataset_root = root / "dataset"
    metadata_root = dataset_root / "metadata"
    split_root = dataset_root / "split" / "eggplant"
    manifest_path = metadata_root / "eggplant_split_manifest.csv"
    summary_path = metadata_root / "eggplant_split_summary.json"
    validation_path = metadata_root / "eggplant_split_validation.csv"
    errors: list[str] = []

    try:
        cleaned_rows, current_cleaned_fingerprint = validate_cleaned_prerequisites(root)
        expected_assignments = generate_assignments(cleaned_rows, DEFAULT_SEED)
        validate_assignments(expected_assignments, cleaned_rows)
        manifest_rows = read_csv(manifest_path, set(SPLIT_MANIFEST_FIELDS))
        if not summary_path.is_file():
            raise BuildError(f"Split summary is missing: {summary_path}")
        split_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        cleaning_summary_path = metadata_root / "eggplant_cleaning_summary.json"
        cleaning_summary = json.loads(cleaning_summary_path.read_text(encoding="utf-8"))
        _, _, current_raw_fingerprint = load_and_plan(root)
    except (BuildError, json.JSONDecodeError) as error:
        return False, {"errors": [str(error)]}

    if manifest_rows != expected_assignments:
        errors.append("Split manifest is not identical to regenerated seed 42 assignment")
    if assignment_digest(manifest_rows) != assignment_digest(expected_assignments):
        errors.append("Split manifest assignment digest mismatch")
    different_seed = generate_assignments(cleaned_rows, DEFAULT_SEED + 1)
    seed_changes_assignment = any(
        left["split"] != right["split"]
        for left, right in zip(expected_assignments, different_seed)
    )
    if not seed_changes_assignment:
        errors.append("Seed 43 did not change any split assignment")

    expected_summary = build_summary(expected_assignments, current_cleaned_fingerprint)
    errors.extend(compare_summary(split_summary, expected_summary))
    cleaned_modified = (
        split_summary.get("cleaned_fingerprint_before_split")
        != current_cleaned_fingerprint
    )
    if cleaned_modified:
        errors.append("Cleaned dataset fingerprint changed after split")
    raw_modified = (
        cleaning_summary.get("raw_fingerprint_before_build") != current_raw_fingerprint
    )
    if raw_modified:
        errors.append("Raw dataset fingerprint changed during D5")

    split_rows, scan_errors = scan_split(split_root)
    errors.extend(scan_errors)
    write_validation(validation_path, split_rows)
    invalid_rows = [row for row in split_rows if row["status"] != "valid"]
    if invalid_rows:
        errors.append(f"Invalid split images: {len(invalid_rows)}")

    manifest_outputs: dict[tuple[str, str, str], dict[str, str]] = {}
    source_splits: dict[tuple[str, str], set[str]] = defaultdict(set)
    hash_splits: dict[str, set[str]] = defaultdict(set)
    for row in manifest_rows:
        try:
            relative = safe_relative_path(row["filename"]).as_posix()
        except BuildError as error:
            errors.append(str(error))
            continue
        key = (row["split"], row["class"], relative)
        if key in manifest_outputs:
            errors.append(f"Duplicate manifest destination: {'/'.join(key)}")
        manifest_outputs[key] = row
        source_splits[(row["class"], relative)].add(row["split"])
        hash_splits[row["sha256"]].add(row["split"])

    actual_outputs: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in split_rows:
        key = (str(row["split"]), str(row["class"]), str(row["filename"]))
        if key in actual_outputs:
            errors.append(f"Duplicate split path: {'/'.join(key)}")
        actual_outputs[key] = row
    if set(manifest_outputs) != set(actual_outputs):
        missing = sorted(set(manifest_outputs) - set(actual_outputs))
        orphan = sorted(set(actual_outputs) - set(manifest_outputs))
        errors.append(f"Split/manifest mismatch; missing={missing[:3]} orphan={orphan[:3]}")
    for key in sorted(set(manifest_outputs) & set(actual_outputs)):
        if manifest_outputs[key]["sha256"] != actual_outputs[key]["sha256"]:
            errors.append(f"Split hash differs from cleaned source: {'/'.join(key)}")

    path_leakage = {
        key: splits for key, splits in source_splits.items() if len(splits) > 1
    }
    sha_leakage = {
        image_hash: splits for image_hash, splits in hash_splits.items() if len(splits) > 1
    }
    if path_leakage:
        errors.append(f"Filename/path leakage across splits: {len(path_leakage)}")
    if sha_leakage:
        errors.append(f"SHA-256 leakage across splits: {len(sha_leakage)}")

    cleaned_sources = {(row["class"], row["filename"]) for row in cleaned_rows}
    if set(source_splits) != cleaned_sources:
        missing = sorted(cleaned_sources - set(source_splits))
        extra = sorted(set(source_splits) - cleaned_sources)
        errors.append(f"Cleaned assignment coverage mismatch; missing={missing[:3]} extra={extra[:3]}")

    counts_per_class = {
        class_name: {
            split_name: sum(
                row["class"] == class_name and row["split"] == split_name
                for row in split_rows
            )
            for split_name in SPLITS
        }
        for class_name in CLASSES
    }
    counts_per_split = Counter(str(row["split"]) for row in split_rows)
    summary_counts = split_summary.get("counts_per_class")
    if counts_per_class != summary_counts:
        errors.append("Actual per-class split counts differ from split summary")

    result: dict[str, object] = {
        "errors": errors,
        "total": len(split_rows),
        "counts_per_class": counts_per_class,
        "counts_per_split": {
            split_name: counts_per_split[split_name] for split_name in SPLITS
        },
        "actual_percentages": {
            split_name: counts_per_split[split_name] / len(split_rows) if split_rows else 0.0
            for split_name in SPLITS
        },
        "invalid": len(invalid_rows),
        "manifest_consistency": not any(
            "manifest" in error.lower() or "assignment coverage" in error.lower()
            for error in errors
        ),
        "hash_consistency": not any("hash" in error.lower() for error in errors),
        "path_leakage": len(path_leakage),
        "sha_leakage": len(sha_leakage),
        "seed_42_reproducible": manifest_rows == expected_assignments,
        "seed_43_changes_assignment": seed_changes_assignment,
        "raw_modified": raw_modified,
        "cleaned_modified": cleaned_modified,
        "validation_report": validation_path.relative_to(root).as_posix(),
    }
    return not errors, result


def print_result(passed: bool, result: dict[str, object]) -> None:
    print("============================")
    print("Eggplant Split Validation")
    print("============================")
    print("\nPer class:")
    for class_name in CLASSES:
        counts = result["counts_per_class"][class_name]  # type: ignore[index]
        print(
            f"  {class_name}: train={counts['train']} val={counts['val']} test={counts['test']}"
        )
    print("\nPer split:")
    for split_name in SPLITS:
        count = result["counts_per_split"][split_name]  # type: ignore[index]
        percentage = result["actual_percentages"][split_name]  # type: ignore[index]
        print(f"  {split_name}: {count} ({percentage:.2%})")
    print(f"  total: {result['total']}")
    print("\nIntegrity:")
    print(f"  invalid images: {result['invalid']}")
    print(f"  hash consistency: {'PASS' if result['hash_consistency'] else 'FAIL'}")
    print(f"  manifest consistency: {'PASS' if result['manifest_consistency'] else 'FAIL'}")
    print("\nLeakage:")
    print(f"  filename/path overlap: {result['path_leakage']}")
    print(f"  SHA-256 overlap: {result['sha_leakage']}")
    print("\nReproducibility:")
    print(f"  seed 42 rerun identical: {'PASS' if result['seed_42_reproducible'] else 'FAIL'}")
    print(f"  seed 43 changes assignment: {'PASS' if result['seed_43_changes_assignment'] else 'FAIL'}")
    print("\nData safety:")
    print(f"  raw modified: {'TRUE' if result['raw_modified'] else 'FALSE'}")
    print(f"  cleaned modified: {'TRUE' if result['cleaned_modified'] else 'FALSE'}")
    print(f"\nValidation report: {result['validation_report']}")
    if result["errors"]:
        print("\nFailures:")
        for error in result["errors"]:  # type: ignore[union-attr]
            print(f"  {error}")
    print(f"\nD5 Result: {'PASS' if passed else 'FAIL'}")


def main() -> int:
    passed, result = validate_split()
    if "counts_per_class" in result:
        print_result(passed, result)
    else:
        print("D5 Result: FAIL")
        for error in result.get("errors", []):  # type: ignore[union-attr]
            print(f"  {error}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
