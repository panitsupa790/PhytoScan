from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Iterable

from build_clean_dataset import (
    CLASS_ORDER,
    CLASSES,
    BuildError,
    safe_relative_path,
    sha256_file,
)


SPLITS = ("train", "val", "test")
SPLIT_ORDER = {split_name: index for index, split_name in enumerate(SPLITS)}
RATIOS = {
    "train": Fraction(75, 100),
    "val": Fraction(10, 100),
    "test": Fraction(15, 100),
}
DEFAULT_SEED = 42
CLEANED_VALIDATION_FIELDS = {
    "class",
    "filename",
    "extension",
    "width",
    "height",
    "mode",
    "sha256",
    "status",
    "error",
}
CLEANED_MANIFEST_FIELDS = {
    "source_class",
    "source_filename",
    "sha256",
    "final_class",
    "action",
    "reason",
    "review_source",
    "reviewer",
}
SPLIT_MANIFEST_FIELDS = ("class", "filename", "sha256", "split", "seed")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_csv(path: Path, required_fields: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise BuildError(f"Required CSV is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fields = set(reader.fieldnames or ())
        missing = sorted(required_fields - fields)
        if missing:
            raise BuildError(f"{path.name} is missing columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def allocate_counts(total: int) -> dict[str, int]:
    if total < 0:
        raise ValueError("Total must not be negative")
    allocation: dict[str, int] = {}
    remainders: list[tuple[Fraction, int, str]] = []
    for split_name in SPLITS:
        exact = total * RATIOS[split_name]
        base = exact.numerator // exact.denominator
        allocation[split_name] = base
        remainders.append((exact - base, -SPLIT_ORDER[split_name], split_name))
    remaining = total - sum(allocation.values())
    for _, _, split_name in sorted(remainders, reverse=True)[:remaining]:
        allocation[split_name] += 1
    if sum(allocation.values()) != total:
        raise BuildError(f"Split allocation does not sum to {total}")
    return allocation


def cleaned_fingerprint(
    cleaned_root: Path,
    validation_rows: list[dict[str, str]],
) -> dict[str, object]:
    expected: dict[tuple[str, str], dict[str, str]] = {}
    for row in validation_rows:
        class_name = row["class"]
        filename = row["filename"]
        if class_name not in CLASSES:
            raise BuildError(f"Unsupported cleaned class: {class_name!r}")
        safe_relative_path(filename)
        key = (class_name, filename)
        if key in expected:
            raise BuildError(f"Duplicate cleaned validation row: {class_name}/{filename}")
        expected[key] = row

    actual: dict[tuple[str, str], Path] = {}
    for class_name in CLASSES:
        class_dir = cleaned_root / class_name
        if not class_dir.is_dir():
            raise BuildError(f"Missing cleaned class directory: {class_dir}")
        for path in class_dir.rglob("*"):
            if path.is_file() and path.name != ".gitkeep":
                actual[(class_name, path.relative_to(class_dir).as_posix())] = path
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise BuildError(
            f"Cleaned files differ from validation report; missing={missing[:3]} extra={extra[:3]}"
        )

    counts: Counter[str] = Counter()
    total_bytes = 0
    digest = hashlib.sha256()
    for key in sorted(actual, key=lambda item: (CLASS_ORDER[item[0]], item[1].casefold(), item[1])):
        row = expected[key]
        if row["status"] != "valid":
            raise BuildError(f"Cleaned validation is not valid: {key[0]}/{key[1]}")
        path = actual[key]
        size = path.stat().st_size
        actual_hash = sha256_file(path)
        if actual_hash != row["sha256"].lower():
            raise BuildError(f"Cleaned hash differs from validation report: {key[0]}/{key[1]}")
        counts[key[0]] += 1
        total_bytes += size
        digest.update(
            f"{key[0]}\0{key[1]}\0{size}\0{actual_hash}\n".encode("utf-8")
        )
    return {
        "class_counts": {class_name: counts[class_name] for class_name in CLASSES},
        "total_files": sum(counts.values()),
        "total_bytes": total_bytes,
        "dataset_sha256": digest.hexdigest(),
    }


def validate_cleaned_prerequisites(
    root: Path,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    dataset_root = root / "dataset"
    metadata_root = dataset_root / "metadata"
    cleaned_root = dataset_root / "cleaned" / "eggplant"
    validation_rows = read_csv(
        metadata_root / "eggplant_cleaned_validation.csv", CLEANED_VALIDATION_FIELDS
    )
    cleaned_manifest = read_csv(
        metadata_root / "eggplant_cleaned_manifest.csv", CLEANED_MANIFEST_FIELDS
    )
    duplicate_rows = read_csv(
        metadata_root / "eggplant_cleaned_duplicates.csv",
        {"sha256", "duplicate_type", "class", "filename"},
    )
    if duplicate_rows:
        raise BuildError("Cleaned duplicate report is not empty")
    summary_path = metadata_root / "eggplant_cleaning_summary.json"
    if not summary_path.is_file():
        raise BuildError(f"Required summary is missing: {summary_path}")
    try:
        cleaning_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BuildError(f"Invalid cleaning summary JSON: {error}") from error
    if cleaning_summary.get("unresolved_reviews") != 0:
        raise BuildError("Cleaning summary contains unresolved reviews")

    valid_rows = [row for row in validation_rows if row["status"] == "valid"]
    if len(valid_rows) != len(validation_rows):
        raise BuildError("Cleaned validation contains invalid images")
    hashes = [row["sha256"].lower() for row in valid_rows]
    if len(hashes) != len(set(hashes)):
        raise BuildError("Cleaned validation contains exact duplicate hashes")

    keep_rows = [row for row in cleaned_manifest if row["action"] == "KEEP"]
    manifest_source = {
        (row["final_class"], row["source_filename"]): row["sha256"].lower()
        for row in keep_rows
    }
    validation_source = {
        (row["class"], row["filename"]): row["sha256"].lower()
        for row in valid_rows
    }
    if manifest_source != validation_source:
        raise BuildError("Cleaned manifest KEEP rows do not match cleaned validation")

    counts = Counter(row["class"] for row in valid_rows)
    summary_counts = cleaning_summary.get("cleaned_counts")
    expected_counts = {class_name: counts[class_name] for class_name in CLASSES}
    if summary_counts != expected_counts or cleaning_summary.get("cleaned_total") != len(valid_rows):
        raise BuildError("Cleaned counts do not match D4 cleaning summary")

    fingerprint = cleaned_fingerprint(cleaned_root, valid_rows)
    return valid_rows, fingerprint


def generate_assignments(
    validation_rows: list[dict[str, str]], seed: int = DEFAULT_SEED
) -> list[dict[str, str]]:
    rows_by_class: dict[str, list[dict[str, str]]] = {class_name: [] for class_name in CLASSES}
    for row in validation_rows:
        rows_by_class[row["class"]].append(row)

    rng = random.Random(seed)
    assignments: list[dict[str, str]] = []
    for class_name in CLASSES:
        rows = sorted(
            rows_by_class[class_name],
            key=lambda row: (row["filename"].casefold(), row["filename"]),
        )
        rng.shuffle(rows)
        allocation = allocate_counts(len(rows))
        offset = 0
        for split_name in SPLITS:
            count = allocation[split_name]
            for row in rows[offset : offset + count]:
                assignments.append(
                    {
                        "class": class_name,
                        "filename": row["filename"],
                        "sha256": row["sha256"].lower(),
                        "split": split_name,
                        "seed": str(seed),
                    }
                )
            offset += count
    return sorted(
        assignments,
        key=lambda row: (
            CLASS_ORDER[row["class"]],
            row["filename"].casefold(),
            row["filename"],
        ),
    )


def assignment_digest(assignments: Iterable[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in assignments:
        digest.update(
            f"{row['class']}\0{row['filename']}\0{row['sha256']}\0{row['split']}\0{row['seed']}\n".encode(
                "utf-8"
            )
        )
    return digest.hexdigest()


def validate_assignments(
    assignments: list[dict[str, str]], validation_rows: list[dict[str, str]]
) -> None:
    expected = {(row["class"], row["filename"]) for row in validation_rows}
    assigned: dict[tuple[str, str], str] = {}
    hash_splits: dict[str, set[str]] = {}
    for row in assignments:
        key = (row["class"], row["filename"])
        if row["split"] not in SPLITS:
            raise BuildError(f"Unsupported split assignment: {row['split']}")
        if key in assigned:
            raise BuildError(f"Image assigned more than once: {key[0]}/{key[1]}")
        assigned[key] = row["split"]
        hash_splits.setdefault(row["sha256"], set()).add(row["split"])
    if set(assigned) != expected:
        raise BuildError("Split assignments do not cover every cleaned image exactly once")
    leaked_hashes = [image_hash for image_hash, splits in hash_splits.items() if len(splits) > 1]
    if leaked_hashes:
        raise BuildError(f"SHA-256 leakage across splits: {len(leaked_hashes)}")


def build_summary(
    assignments: list[dict[str, str]], fingerprint: dict[str, object]
) -> dict[str, object]:
    per_class = {
        class_name: {
            split_name: sum(
                row["class"] == class_name and row["split"] == split_name
                for row in assignments
            )
            for split_name in SPLITS
        }
        for class_name in CLASSES
    }
    per_split = {
        split_name: sum(row["split"] == split_name for row in assignments)
        for split_name in SPLITS
    }
    total = len(assignments)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": DEFAULT_SEED,
        "ratios": {split_name: float(RATIOS[split_name]) for split_name in SPLITS},
        "allocation_method": "largest_remainder_per_class",
        "cleaned_fingerprint_before_split": fingerprint,
        "total": total,
        "counts_per_class": per_class,
        "counts_per_split": per_split,
        "actual_percentages": {
            split_name: per_split[split_name] / total if total else 0.0
            for split_name in SPLITS
        },
        "assignment_sha256": assignment_digest(assignments),
        "policies": {
            "test_set": "FROZEN after D5; use only for final evaluation and never for tuning or selection",
            "validation_set": "Use for model selection hyperparameter tuning preprocessing comparison and early stopping",
            "augmentation": "Apply only after splitting and only to train; never augment val or test",
            "class_imbalance": "Preserved in D5; no under-sampling over-sampling class weighting or augmentation applied",
            "near_duplicate_limitation": "Exact duplicate leakage is prevented; near-duplicate or same-leaf sequence leakage was not deeply assessed because no reliable grouping metadata is available",
        },
    }


def existing_split_files(split_root: Path) -> list[Path]:
    if not split_root.exists():
        return []
    return sorted(
        path for path in split_root.rglob("*") if path.is_file() and path.name != ".gitkeep"
    )


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SPLIT_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def apply_assignments(
    root: Path,
    assignments: list[dict[str, str]],
    summary: dict[str, object],
) -> None:
    dataset_root = root / "dataset"
    cleaned_root = dataset_root / "cleaned" / "eggplant"
    split_root = dataset_root / "split" / "eggplant"
    metadata_root = dataset_root / "metadata"
    manifest_path = metadata_root / "eggplant_split_manifest.csv"
    summary_path = metadata_root / "eggplant_split_summary.json"
    existing = existing_split_files(split_root)
    if existing:
        raise BuildError(f"Split output contains {len(existing)} file(s); refusing to overwrite")
    if manifest_path.exists() or summary_path.exists():
        raise BuildError("Split reports already exist; refusing to overwrite")

    created_files: list[Path] = []
    try:
        for row in assignments:
            relative_path = safe_relative_path(row["filename"])
            source = cleaned_root / row["class"] / relative_path
            destination = split_root / row["split"] / row["class"] / relative_path
            if destination.exists():
                raise BuildError(f"Split filename collision: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            created_files.append(destination)
            if sha256_file(destination) != row["sha256"]:
                raise BuildError(f"Split copy hash mismatch: {destination}")
        write_manifest(manifest_path, assignments)
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except Exception:
        for path in reversed(created_files):
            if path.is_file():
                path.unlink()
        if manifest_path.is_file():
            manifest_path.unlink()
        if summary_path.is_file():
            summary_path.unlink()
        raise


def print_plan(summary: dict[str, object], mode: str) -> None:
    print("============================")
    print("Eggplant Split Plan")
    print("============================")
    print(f"Mode: {mode}")
    print(f"Seed: {summary['seed']}")
    print("Ratios: train=75% val=10% test=15%")
    print("Allocation: largest remainder per class")
    print("\nPer class:")
    for class_name in CLASSES:
        counts = summary["counts_per_class"][class_name]  # type: ignore[index]
        print(
            f"  {class_name}: train={counts['train']} val={counts['val']} test={counts['test']} "
            f"total={sum(counts.values())}"
        )
    print("\nPer split:")
    for split_name in SPLITS:
        count = summary["counts_per_split"][split_name]  # type: ignore[index]
        percentage = summary["actual_percentages"][split_name]  # type: ignore[index]
        print(f"  {split_name}: {count} ({percentage:.2%})")
    print(f"  total: {summary['total']}")
    print(f"\nAssignment SHA-256: {summary['assignment_sha256']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a reproducible eggplant split")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy images and write split reports (default: dry-run)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    try:
        validation_rows, fingerprint = validate_cleaned_prerequisites(root)
        assignments = generate_assignments(validation_rows, DEFAULT_SEED)
        validate_assignments(assignments, validation_rows)
        repeat = generate_assignments(validation_rows, DEFAULT_SEED)
        if assignments != repeat:
            raise BuildError("Seed 42 assignment is not reproducible")
        different_seed = generate_assignments(validation_rows, DEFAULT_SEED + 1)
        if all(
            first["split"] == second["split"]
            for first, second in zip(assignments, different_seed)
        ):
            raise BuildError("Seed does not affect split assignments")
        existing = existing_split_files(root / "dataset" / "split" / "eggplant")
        if existing:
            raise BuildError(f"Split output contains {len(existing)} file(s); refusing to overwrite")
        summary = build_summary(assignments, fingerprint)
        print_plan(summary, "APPLY" if args.apply else "DRY RUN")
        print("Reproducibility check (seed 42): PASS")
        print("Different-seed check (seed 43): PASS")
        if args.apply:
            apply_assignments(root, assignments, summary)
            print("\nSplit completed. Files were copied from cleaned to split.")
        else:
            print("\nDry-run only. No split files or reports were written.")
        return 0
    except BuildError as error:
        print(f"SPLIT FAILED: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
