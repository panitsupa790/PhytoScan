from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from build_clean_dataset import (
    CLASS_ORDER,
    CLASSES,
    MANIFEST_FIELDS,
    BuildError,
    build_summary,
    image_key,
    load_and_plan,
    safe_relative_path,
)
from validate_dataset import (
    DUPLICATE_FIELDS,
    SUPPORTED_EXTENSIONS,
    VALIDATION_FIELDS,
    duplicate_rows,
    validate_image,
    write_csv,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise BuildError(f"Cleaned manifest is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fields = set(reader.fieldnames or ())
        missing = sorted(set(MANIFEST_FIELDS) - fields)
        if missing:
            raise BuildError(f"Cleaned manifest is missing columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def scan_cleaned(cleaned_root: Path) -> tuple[list[dict[str, object]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, object]] = []
    if not cleaned_root.is_dir():
        return rows, [f"Missing cleaned dataset directory: {cleaned_root}"]

    unknown_dirs = sorted(
        path.name
        for path in cleaned_root.iterdir()
        if path.is_dir() and path.name not in CLASSES
    )
    if unknown_dirs:
        errors.append(f"Unknown class directories: {', '.join(unknown_dirs)}")
    root_files = sorted(
        path.name
        for path in cleaned_root.iterdir()
        if path.is_file() and path.name != ".gitkeep"
    )
    if root_files:
        errors.append(f"Files found at cleaned dataset root: {', '.join(root_files[:5])}")

    for class_name in CLASSES:
        class_dir = cleaned_root / class_name
        if not class_dir.is_dir():
            errors.append(f"Missing cleaned class directory: {class_name}")
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
                errors.append(f"Unsupported cleaned file: {class_name}/{path.name}")
            rows.append(validate_image(path, class_name, class_dir))
    return rows, errors


def manifest_map(
    rows: list[dict[str, str]],
) -> tuple[dict[tuple[str, str], dict[str, str]], list[str]]:
    errors: list[str] = []
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        try:
            key = image_key(row["source_class"], row["source_filename"])
        except BuildError as error:
            errors.append(str(error))
            continue
        if key in result:
            errors.append(f"Duplicate source row in manifest: {key[0]}/{key[1]}")
        result[key] = row
        if row["action"] not in {"KEEP", "REJECT", "DEDUPLICATED"}:
            errors.append(f"Unsupported manifest action for {key}: {row['action']}")
        if row["action"] == "KEEP":
            if row["final_class"] not in CLASSES:
                errors.append(f"Invalid final class for KEEP row {key}: {row['final_class']}")
        elif row["final_class"]:
            errors.append(f"Non-KEEP manifest row has final class: {key}")
    return result, errors


def expected_output_map(
    manifest_rows: list[dict[str, str]],
) -> tuple[dict[tuple[str, str], dict[str, str]], list[str]]:
    outputs: dict[tuple[str, str], dict[str, str]] = {}
    errors: list[str] = []
    for row in manifest_rows:
        if row["action"] != "KEEP":
            continue
        try:
            relative = safe_relative_path(row["source_filename"]).as_posix()
        except BuildError as error:
            errors.append(str(error))
            continue
        key = (row["final_class"], relative)
        if key in outputs:
            errors.append(f"Manifest output collision: {key[0]}/{key[1]}")
        outputs[key] = row
    return outputs, errors


def compare_manifest_to_plan(
    manifest_rows: list[dict[str, str]],
    expected_plan: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    actual, map_errors = manifest_map(manifest_rows)
    errors.extend(map_errors)
    expected = {
        (row["source_class"], row["source_filename"]): row for row in expected_plan
    }
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        errors.append(f"Manifest source coverage mismatch; missing={missing[:3]} extra={extra[:3]}")
    for key in sorted(set(actual) & set(expected)):
        for field in MANIFEST_FIELDS:
            if actual[key].get(field, "") != expected[key].get(field, ""):
                errors.append(
                    f"Manifest differs from cleaning plan for {key[0]}/{key[1]} field {field}"
                )
                break
    return errors


def compare_summary(
    summary: dict[str, object], expected_summary: dict[str, object]
) -> list[str]:
    errors: list[str] = []
    fields = (
        "raw_fingerprint_before_build",
        "raw_counts",
        "cleaned_counts",
        "raw_total",
        "cleaned_total",
        "retention_rate",
        "action_counts",
        "reason_counts",
        "removed_by_category",
        "resolved_conflicts",
        "unresolved_reviews",
        "manifest_rows",
    )
    for field in fields:
        if summary.get(field) != expected_summary.get(field):
            errors.append(f"Cleaning summary differs from current plan: {field}")
    return errors


def validate_cleaned() -> tuple[bool, dict[str, object]]:
    root = project_root()
    dataset_root = root / "dataset"
    metadata_root = dataset_root / "metadata"
    cleaned_root = dataset_root / "cleaned" / "eggplant"
    manifest_path = metadata_root / "eggplant_cleaned_manifest.csv"
    summary_path = metadata_root / "eggplant_cleaning_summary.json"
    validation_path = metadata_root / "eggplant_cleaned_validation.csv"
    duplicate_path = metadata_root / "eggplant_cleaned_duplicates.csv"

    errors: list[str] = []
    try:
        expected_plan, conflicts, current_raw_fingerprint = load_and_plan(root)
        expected_summary = build_summary(
            expected_plan, conflicts, current_raw_fingerprint
        )
        manifest_rows = read_manifest(manifest_path)
        if not summary_path.is_file():
            raise BuildError(f"Cleaning summary is missing: {summary_path}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (BuildError, json.JSONDecodeError) as error:
        return False, {"errors": [str(error)]}

    errors.extend(compare_manifest_to_plan(manifest_rows, expected_plan))
    errors.extend(compare_summary(summary, expected_summary))
    if summary.get("raw_fingerprint_before_build") != current_raw_fingerprint:
        errors.append("Raw fingerprint changed after D4.3")

    cleaned_rows, scan_errors = scan_cleaned(cleaned_root)
    errors.extend(scan_errors)
    duplicates, duplicate_group_count, same_class_groups, cross_class_groups = duplicate_rows(
        cleaned_rows
    )
    write_csv(validation_path, VALIDATION_FIELDS, cleaned_rows)
    write_csv(duplicate_path, DUPLICATE_FIELDS, duplicates)

    invalid_rows = [row for row in cleaned_rows if row["status"] != "valid"]
    if invalid_rows:
        errors.append(f"Invalid cleaned images: {len(invalid_rows)}")
    if duplicate_group_count:
        errors.append(f"Exact duplicate groups remain: {duplicate_group_count}")

    output_manifest, output_errors = expected_output_map(manifest_rows)
    errors.extend(output_errors)
    actual_output: dict[tuple[str, str], dict[str, object]] = {}
    for row in cleaned_rows:
        key = (str(row["class"]), str(row["filename"]))
        if key in actual_output:
            errors.append(f"Duplicate cleaned output path: {key[0]}/{key[1]}")
        actual_output[key] = row
    if set(output_manifest) != set(actual_output):
        missing = sorted(set(output_manifest) - set(actual_output))
        orphan = sorted(set(actual_output) - set(output_manifest))
        errors.append(f"Cleaned/manifest mismatch; missing={missing[:3]} orphan={orphan[:3]}")
    for key in sorted(set(output_manifest) & set(actual_output)):
        if output_manifest[key]["sha256"] != actual_output[key]["sha256"]:
            errors.append(f"Hash mismatch for cleaned output: {key[0]}/{key[1]}")

    class_counts = Counter(str(row["class"]) for row in cleaned_rows)
    expected_counts = expected_summary["cleaned_counts"]
    for class_name in CLASSES:
        if class_counts[class_name] != expected_counts[class_name]:  # type: ignore[index]
            errors.append(f"Cleaned class count mismatch: {class_name}")

    result: dict[str, object] = {
        "errors": errors,
        "raw_counts": current_raw_fingerprint["class_counts"],
        "raw_total": current_raw_fingerprint["total_files"],
        "cleaned_counts": {class_name: class_counts[class_name] for class_name in CLASSES},
        "cleaned_total": len(cleaned_rows),
        "retention_rate": len(cleaned_rows) / int(current_raw_fingerprint["total_files"]),
        "removed_by_category": expected_summary["removed_by_category"],
        "valid": len(cleaned_rows) - len(invalid_rows),
        "invalid": len(invalid_rows),
        "duplicate_groups": duplicate_group_count,
        "same_class_duplicate_groups": same_class_groups,
        "cross_class_duplicate_groups": cross_class_groups,
        "unresolved_reviews": 0,
        "manifest_consistency": not any("Manifest" in error or "manifest" in error for error in errors),
        "hash_consistency": not any("Hash mismatch" in error for error in errors),
        "raw_modified": summary.get("raw_fingerprint_before_build") != current_raw_fingerprint,
        "reports": [
            validation_path.relative_to(root).as_posix(),
            duplicate_path.relative_to(root).as_posix(),
        ],
    }
    return not errors, result


def print_result(passed: bool, result: dict[str, object]) -> None:
    print("================================")
    print("Cleaned Eggplant Dataset Summary")
    print("================================")
    print("\nRaw:")
    for class_name in CLASSES:
        print(f"  {class_name}: {result['raw_counts'][class_name]}")  # type: ignore[index]
    print(f"  total: {result['raw_total']}")
    print("\nCleaned:")
    for class_name in CLASSES:
        print(f"  {class_name}: {result['cleaned_counts'][class_name]}")  # type: ignore[index]
    print(f"  total: {result['cleaned_total']}")
    print(f"\nRetention: {result['retention_rate']:.2%}")
    print("\nRemoved / excluded:")
    for reason, count in result["removed_by_category"].items():  # type: ignore[union-attr]
        print(f"  {reason}: {count}")
    print("\nIntegrity:")
    print(f"  valid: {result['valid']}")
    print(f"  invalid: {result['invalid']}")
    print("\nExact duplicate groups:")
    print(f"  total: {result['duplicate_groups']}")
    print(f"  same-class: {result['same_class_duplicate_groups']}")
    print(f"  cross-class: {result['cross_class_duplicate_groups']}")
    print(f"\nReview unresolved: {result['unresolved_reviews']}")
    print(f"Manifest consistency: {'PASS' if result['manifest_consistency'] else 'FAIL'}")
    print(f"Hash consistency: {'PASS' if result['hash_consistency'] else 'FAIL'}")
    print(f"Raw modified: {'TRUE' if result['raw_modified'] else 'FALSE'}")
    print("\nReports:")
    for path in result["reports"]:  # type: ignore[union-attr]
        print(f"  {path}")
    errors = result.get("errors", [])
    if errors:
        print("\nFailures:")
        for error in errors:  # type: ignore[union-attr]
            print(f"  {error}")
    print(f"\nD4.4 Result: {'PASS' if passed else 'FAIL'}")


def main() -> int:
    passed, result = validate_cleaned()
    if "raw_counts" in result:
        print_result(passed, result)
    else:
        print("D4.4 Result: FAIL")
        for error in result.get("errors", []):  # type: ignore[union-attr]
            print(f"  {error}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
