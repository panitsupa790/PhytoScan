from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable


CLASSES = ("healthy", "leaf_spot", "mosaic_virus")
CLASS_ORDER = {class_name: index for index, class_name in enumerate(CLASSES)}
VALIDATION_FIELDS = {
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
DUPLICATE_FIELDS = {"sha256", "duplicate_type", "class", "filename"}
CROSS_REVIEW_FIELDS = {
    "group_id",
    "sha256",
    "class_a",
    "filename_a",
    "class_b",
    "filename_b",
    "decision",
    "reviewer",
    "notes",
}
RESOLUTION_REVIEW_FIELDS = {
    "class",
    "filename",
    "width",
    "height",
    "decision",
    "reviewer",
    "notes",
}
AUDIT_REVIEW_FIELDS = {
    "class",
    "filename",
    "review_status",
    "reviewer",
    "notes",
}
MANIFEST_FIELDS = (
    "source_class",
    "source_filename",
    "sha256",
    "final_class",
    "action",
    "reason",
    "review_source",
    "reviewer",
)
CROSS_DECISIONS = {
    "KEEP_HEALTHY": "healthy",
    "KEEP_LEAF_SPOT": "leaf_spot",
    "KEEP_MOSAIC_VIRUS": "mosaic_virus",
}
CROSS_ALLOWED = {*CROSS_DECISIONS, "REJECT_BOTH", "NEEDS_EXPERT_REVIEW"}
RESOLUTION_ALLOWED = {"KEEP", "REJECT", "NEEDS_EXPERT_REVIEW"}
AUDIT_ALLOWED = {"CORRECT", "INCORRECT", "UNCERTAIN"}
HASH_CHUNK_SIZE = 1024 * 1024


class BuildError(RuntimeError):
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def safe_relative_path(filename: str) -> Path:
    pure_path = PurePosixPath(filename.replace("\\", "/"))
    if pure_path.is_absolute() or not pure_path.parts or any(
        part in {"", ".", ".."} for part in pure_path.parts
    ):
        raise BuildError(f"Unsafe relative filename in metadata: {filename!r}")
    return Path(*pure_path.parts)


def image_key(class_name: str, filename: str) -> tuple[str, str]:
    if class_name not in CLASSES:
        raise BuildError(f"Unsupported class: {class_name!r}")
    safe_relative_path(filename)
    return class_name, filename


def ensure_unique_keys(
    rows: Iterable[dict[str, str]],
    key_fields: tuple[str, ...],
    report_name: str,
) -> None:
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        if key in seen:
            raise BuildError(f"Duplicate key in {report_name}: {key}")
        seen.add(key)


def validate_review_value(
    value: str,
    allowed: set[str],
    unresolved: str,
    context: str,
) -> None:
    if not value:
        raise BuildError(f"Blank review decision: {context}")
    if value not in allowed:
        raise BuildError(f"Unsupported review decision {value!r}: {context}")
    if value == unresolved:
        raise BuildError(f"Unresolved review decision: {context}")


def validate_inputs(
    validation_rows: list[dict[str, str]],
    duplicate_rows: list[dict[str, str]],
    cross_rows: list[dict[str, str]],
    resolution_rows: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
) -> None:
    ensure_unique_keys(validation_rows, ("class", "filename"), "validation report")
    validation_by_key: dict[tuple[str, str], dict[str, str]] = {}
    hashes: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in validation_rows:
        key = image_key(row["class"], row["filename"])
        validation_by_key[key] = row
        if row["status"] == "valid":
            image_hash = row["sha256"].lower()
            if len(image_hash) != 64 or any(char not in "0123456789abcdef" for char in image_hash):
                raise BuildError(f"Invalid SHA-256 for {key[0]}/{key[1]}")
            hashes[image_hash].append(key)

    expected_duplicate_rows: set[tuple[str, str, str, str]] = set()
    expected_cross_hashes: set[str] = set()
    for image_hash, keys in hashes.items():
        if len(keys) < 2:
            continue
        duplicate_type = "same_class" if len({key[0] for key in keys}) == 1 else "cross_class"
        if duplicate_type == "cross_class":
            expected_cross_hashes.add(image_hash)
        expected_duplicate_rows.update(
            (image_hash, duplicate_type, class_name, filename)
            for class_name, filename in keys
        )

    actual_duplicate_rows: set[tuple[str, str, str, str]] = set()
    for row in duplicate_rows:
        key = image_key(row["class"], row["filename"])
        item = (row["sha256"].lower(), row["duplicate_type"], *key)
        if item in actual_duplicate_rows:
            raise BuildError(f"Duplicate row in duplicate report: {item}")
        actual_duplicate_rows.add(item)
    if actual_duplicate_rows != expected_duplicate_rows:
        raise BuildError("Duplicate report does not match validation hashes")

    ensure_unique_keys(cross_rows, ("sha256",), "cross-class review")
    reviewed_cross_hashes: set[str] = set()
    for row in cross_rows:
        image_hash = row["sha256"].lower()
        reviewed_cross_hashes.add(image_hash)
        validate_review_value(
            row["decision"], CROSS_ALLOWED, "NEEDS_EXPERT_REVIEW", row["group_id"]
        )
        if not row["reviewer"].strip():
            raise BuildError(f"Blank reviewer in cross-class review: {row['group_id']}")
        listed_keys = {
            image_key(row["class_a"], row["filename_a"]),
            image_key(row["class_b"], row["filename_b"]),
        }
        actual_keys = set(hashes.get(image_hash, ()))
        if listed_keys != actual_keys:
            raise BuildError(f"Cross-class review members do not match hash: {row['group_id']}")
        selected_class = CROSS_DECISIONS.get(row["decision"])
        if selected_class and selected_class not in {key[0] for key in listed_keys}:
            raise BuildError(f"Selected class is absent from group: {row['group_id']}")
    if reviewed_cross_hashes != expected_cross_hashes:
        raise BuildError("Cross-class review does not cover every cross-class duplicate group")

    ensure_unique_keys(resolution_rows, ("class", "filename"), "resolution review")
    reviewed_resolution: set[tuple[str, str]] = set()
    for row in resolution_rows:
        key = image_key(row["class"], row["filename"])
        reviewed_resolution.add(key)
        validate_review_value(
            row["decision"], RESOLUTION_ALLOWED, "NEEDS_EXPERT_REVIEW", f"{key[0]}/{key[1]}"
        )
        if not row["reviewer"].strip():
            raise BuildError(f"Blank reviewer in resolution review: {key[0]}/{key[1]}")
        validation_row = validation_by_key.get(key)
        if validation_row is None:
            raise BuildError(f"Resolution review image is absent from validation report: {key}")
        if (row["width"], row["height"]) != (
            validation_row["width"],
            validation_row["height"],
        ):
            raise BuildError(f"Resolution review dimensions do not match validation report: {key}")
    expected_resolution = {
        key
        for key, row in validation_by_key.items()
        if key[0] == "mosaic_virus" and row["width"] == "256" and row["height"] == "256"
    }
    if reviewed_resolution != expected_resolution:
        raise BuildError("Resolution review does not exactly cover mosaic_virus 256x256 images")

    ensure_unique_keys(audit_rows, ("class", "filename"), "random audit")
    audit_counts: Counter[str] = Counter()
    for row in audit_rows:
        key = image_key(row["class"], row["filename"])
        validate_review_value(
            row["review_status"], AUDIT_ALLOWED, "UNCERTAIN", f"{key[0]}/{key[1]}"
        )
        if not row["reviewer"].strip():
            raise BuildError(f"Blank reviewer in random audit: {key[0]}/{key[1]}")
        if key not in validation_by_key:
            raise BuildError(f"Random audit image is absent from validation report: {key}")
        audit_counts[key[0]] += 1
    if any(audit_counts[class_name] != 50 for class_name in CLASSES):
        raise BuildError(f"Random audit must contain 50 rows per class; found {dict(audit_counts)}")


def raw_fingerprint(
    raw_root: Path,
    validation_rows: list[dict[str, str]],
) -> tuple[dict[str, object], dict[tuple[str, str], str]]:
    expected = {
        image_key(row["class"], row["filename"]): row for row in validation_rows
    }
    actual_paths: dict[tuple[str, str], Path] = {}
    for class_name in CLASSES:
        class_dir = raw_root / class_name
        if not class_dir.is_dir():
            raise BuildError(f"Missing raw class directory: {class_dir}")
        for path in class_dir.rglob("*"):
            if path.is_file() and path.name != ".gitkeep":
                filename = path.relative_to(class_dir).as_posix()
                actual_paths[(class_name, filename)] = path
    if set(actual_paths) != set(expected):
        missing = sorted(set(expected) - set(actual_paths))
        extra = sorted(set(actual_paths) - set(expected))
        raise BuildError(
            f"Raw files differ from validation report; missing={missing[:3]} extra={extra[:3]}"
        )

    counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    total_bytes = 0
    actual_hashes: dict[tuple[str, str], str] = {}
    dataset_digest = hashlib.sha256()
    for key in sorted(actual_paths, key=lambda item: (CLASS_ORDER[item[0]], item[1].casefold(), item[1])):
        path = actual_paths[key]
        size = path.stat().st_size
        image_hash = sha256_file(path)
        row = expected[key]
        if row["status"] == "valid" and image_hash != row["sha256"].lower():
            raise BuildError(f"Raw hash differs from validation report: {key[0]}/{key[1]}")
        counts[key[0]] += 1
        extension_counts[path.suffix.lower()] += 1
        total_bytes += size
        actual_hashes[key] = image_hash
        dataset_digest.update(
            f"{key[0]}\0{key[1]}\0{size}\0{image_hash}\n".encode("utf-8")
        )

    fingerprint: dict[str, object] = {
        "class_counts": {class_name: counts[class_name] for class_name in CLASSES},
        "total_files": sum(counts.values()),
        "total_bytes": total_bytes,
        "extension_counts": dict(sorted(extension_counts.items())),
        "dataset_sha256": dataset_digest.hexdigest(),
    }
    return fingerprint, actual_hashes


def review_references(
    cross_rows: list[dict[str, str]],
    resolution_rows: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
) -> dict[tuple[str, str], list[tuple[str, str]]]:
    references: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for row in cross_rows:
        for key in (
            image_key(row["class_a"], row["filename_a"]),
            image_key(row["class_b"], row["filename_b"]),
        ):
            references[key].append(("cross_class", row["reviewer"]))
    for row in resolution_rows:
        references[image_key(row["class"], row["filename"])].append(
            ("resolution", row["reviewer"])
        )
    for row in audit_rows:
        references[image_key(row["class"], row["filename"])].append(
            ("random_audit", row["reviewer"])
        )
    return references


def ordered_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def create_plan(
    validation_rows: list[dict[str, str]],
    duplicate_rows: list[dict[str, str]],
    cross_rows: list[dict[str, str]],
    resolution_rows: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    validation_by_key = {
        image_key(row["class"], row["filename"]): row for row in validation_rows
    }
    plan: dict[tuple[str, str], dict[str, str]] = {}
    for key, row in validation_by_key.items():
        valid = row["status"] == "valid"
        plan[key] = {
            "source_class": key[0],
            "source_filename": key[1],
            "sha256": row["sha256"].lower(),
            "final_class": key[0] if valid else "",
            "action": "KEEP" if valid else "REJECT",
            "reason": "NORMAL_VALID_IMAGE" if valid else "INVALID_IMAGE",
            "review_source": "",
            "reviewer": "",
        }

    resolution_by_key = {
        image_key(row["class"], row["filename"]): row for row in resolution_rows
    }
    audit_by_key = {
        image_key(row["class"], row["filename"]): row for row in audit_rows
    }
    for key, row in resolution_by_key.items():
        if row["decision"] == "REJECT":
            plan[key].update(
                action="REJECT", final_class="", reason="RESOLUTION_REJECT"
            )
    for key, row in audit_by_key.items():
        if row["review_status"] == "INCORRECT" and plan[key]["reason"] != "RESOLUTION_REJECT":
            plan[key].update(
                action="REJECT", final_class="", reason="RANDOM_AUDIT_INCORRECT"
            )

    duplicate_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    duplicate_types: dict[str, str] = {}
    for row in duplicate_rows:
        image_hash = row["sha256"].lower()
        duplicate_groups[image_hash].append(image_key(row["class"], row["filename"]))
        duplicate_types[image_hash] = row["duplicate_type"]

    conflicts: list[dict[str, str]] = []
    cross_by_hash = {row["sha256"].lower(): row for row in cross_rows}
    for image_hash, row in sorted(cross_by_hash.items()):
        members = duplicate_groups[image_hash]
        decision = row["decision"]
        if decision == "REJECT_BOTH":
            for key in members:
                if plan[key]["action"] == "KEEP":
                    plan[key].update(
                        action="REJECT",
                        final_class="",
                        reason="CROSS_CLASS_REJECT_BOTH",
                    )
            continue

        selected_class = CROSS_DECISIONS[decision]
        candidates = sorted(
            (key for key in members if key[0] == selected_class),
            key=lambda key: (key[1].casefold(), key[1]),
        )
        canonical = candidates[0]
        for key in members:
            if key == canonical:
                if plan[key]["action"] == "KEEP":
                    plan[key]["reason"] = decision.replace("KEEP_", "CROSS_CLASS_KEEP_")
                    plan[key]["final_class"] = selected_class
                else:
                    conflicts.append(
                        {
                            "group_id": row["group_id"],
                            "selected_file": f"{key[0]}/{key[1]}",
                            "cross_decision": decision,
                            "higher_priority_reason": plan[key]["reason"],
                            "resolution": "selected file excluded; non-selected duplicates remain excluded",
                        }
                    )
            elif plan[key]["action"] == "KEEP":
                plan[key].update(
                    action="DEDUPLICATED",
                    final_class="",
                    reason=decision.replace("KEEP_", "CROSS_CLASS_KEEP_"),
                )

    for image_hash, members in sorted(duplicate_groups.items()):
        if duplicate_types[image_hash] != "same_class":
            continue
        eligible = sorted(
            (key for key in members if plan[key]["action"] == "KEEP"),
            key=lambda key: (key[1].casefold(), key[1]),
        )
        canonical = eligible[0] if eligible else None
        for key in members:
            if key != canonical and plan[key]["action"] == "KEEP":
                plan[key].update(
                    action="DEDUPLICATED",
                    final_class="",
                    reason="SAME_CLASS_EXACT_DUPLICATE",
                )

    references = review_references(cross_rows, resolution_rows, audit_rows)
    for key, manifest_row in plan.items():
        refs = references.get(key, ())
        manifest_row["review_source"] = "|".join(
            ordered_unique(source for source, _ in refs)
        )
        manifest_row["reviewer"] = "|".join(
            ordered_unique(reviewer for _, reviewer in refs)
        )

    rows = sorted(
        plan.values(),
        key=lambda row: (
            CLASS_ORDER[row["source_class"]],
            row["source_filename"].casefold(),
            row["source_filename"],
        ),
    )
    return rows, conflicts


def load_and_plan(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    dataset_root = root / "dataset"
    metadata_root = dataset_root / "metadata"
    validation_rows = read_csv(metadata_root / "eggplant_validation.csv", VALIDATION_FIELDS)
    duplicate_rows = read_csv(metadata_root / "eggplant_duplicates.csv", DUPLICATE_FIELDS)
    cross_rows = read_csv(
        metadata_root / "eggplant_cross_class_review.csv", CROSS_REVIEW_FIELDS
    )
    resolution_rows = read_csv(
        metadata_root / "eggplant_resolution_review.csv", RESOLUTION_REVIEW_FIELDS
    )
    audit_rows = read_csv(
        metadata_root / "eggplant_random_audit.csv", AUDIT_REVIEW_FIELDS
    )
    validate_inputs(
        validation_rows, duplicate_rows, cross_rows, resolution_rows, audit_rows
    )
    fingerprint, actual_hashes = raw_fingerprint(
        dataset_root / "raw" / "eggplant", validation_rows
    )
    for row in validation_rows:
        key = image_key(row["class"], row["filename"])
        if row["status"] == "valid" and actual_hashes[key] != row["sha256"].lower():
            raise BuildError(f"Raw validation mismatch: {key[0]}/{key[1]}")
    plan, conflicts = create_plan(
        validation_rows, duplicate_rows, cross_rows, resolution_rows, audit_rows
    )
    return plan, conflicts, fingerprint


def build_summary(
    plan: list[dict[str, str]],
    conflicts: list[dict[str, str]],
    fingerprint: dict[str, object],
) -> dict[str, object]:
    cleaned_counts = Counter(
        row["final_class"] for row in plan if row["action"] == "KEEP"
    )
    action_counts = Counter(row["action"] for row in plan)
    reason_counts = Counter(row["reason"] for row in plan)
    removed_rows = [row for row in plan if row["action"] != "KEEP"]
    removed_by_category = {
        "same_class_duplicates": sum(
            row["reason"] == "SAME_CLASS_EXACT_DUPLICATE" for row in removed_rows
        ),
        "cross_class": sum(
            row["reason"].startswith("CROSS_CLASS_") for row in removed_rows
        ),
        "cross_class_reject_both": sum(
            row["reason"] == "CROSS_CLASS_REJECT_BOTH" for row in removed_rows
        ),
        "resolution": sum(
            row["reason"] == "RESOLUTION_REJECT" for row in removed_rows
        ),
        "random_audit": sum(
            row["reason"] == "RANDOM_AUDIT_INCORRECT" for row in removed_rows
        ),
        "invalid": sum(row["reason"] == "INVALID_IMAGE" for row in removed_rows),
    }
    cleaned_total = action_counts["KEEP"]
    raw_total = int(fingerprint["total_files"])
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_fingerprint_before_build": fingerprint,
        "raw_counts": fingerprint["class_counts"],
        "cleaned_counts": {
            class_name: cleaned_counts[class_name] for class_name in CLASSES
        },
        "raw_total": raw_total,
        "cleaned_total": cleaned_total,
        "retention_rate": cleaned_total / raw_total if raw_total else 0.0,
        "action_counts": dict(sorted(action_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "removed_by_category": removed_by_category,
        "resolved_conflicts": conflicts,
        "unresolved_reviews": 0,
        "manifest_rows": len(plan),
    }


def existing_cleaned_files(cleaned_root: Path) -> list[Path]:
    if not cleaned_root.exists():
        return []
    return sorted(
        path for path in cleaned_root.rglob("*") if path.is_file() and path.name != ".gitkeep"
    )


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def apply_plan(root: Path, plan: list[dict[str, str]], summary: dict[str, object]) -> None:
    dataset_root = root / "dataset"
    raw_root = dataset_root / "raw" / "eggplant"
    cleaned_root = dataset_root / "cleaned" / "eggplant"
    metadata_root = dataset_root / "metadata"
    manifest_path = metadata_root / "eggplant_cleaned_manifest.csv"
    summary_path = metadata_root / "eggplant_cleaning_summary.json"

    existing = existing_cleaned_files(cleaned_root)
    if existing:
        raise BuildError(
            f"Cleaned output already contains {len(existing)} file(s); refusing to overwrite"
        )
    if manifest_path.exists() or summary_path.exists():
        raise BuildError("Cleaning reports already exist; refusing to overwrite")

    created_files: list[Path] = []
    try:
        for row in plan:
            if row["action"] != "KEEP":
                continue
            source = raw_root / row["source_class"] / safe_relative_path(
                row["source_filename"]
            )
            destination = cleaned_root / row["final_class"] / safe_relative_path(
                row["source_filename"]
            )
            if destination.exists():
                raise BuildError(f"Cleaned filename collision: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            created_files.append(destination)
            if sha256_file(destination) != row["sha256"]:
                raise BuildError(f"Copied file hash mismatch: {destination}")
        write_manifest(manifest_path, plan)
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


def print_summary(summary: dict[str, object], mode: str) -> None:
    print("================================")
    print("Cleaned Eggplant Dataset Plan")
    print("================================")
    print(f"Mode: {mode}")
    print("\nRaw:")
    for class_name in CLASSES:
        print(f"  {class_name}: {summary['raw_counts'][class_name]}")  # type: ignore[index]
    print(f"  total: {summary['raw_total']}")
    print("\nCleaned:")
    for class_name in CLASSES:
        print(f"  {class_name}: {summary['cleaned_counts'][class_name]}")  # type: ignore[index]
    print(f"  total: {summary['cleaned_total']}")
    print(f"\nRetention: {summary['retention_rate']:.2%}")
    print("\nActions:")
    for action, count in summary["action_counts"].items():  # type: ignore[union-attr]
        print(f"  {action}: {count}")
    print("\nReasons:")
    for reason, count in summary["reason_counts"].items():  # type: ignore[union-attr]
        print(f"  {reason}: {count}")
    print("\nRemoved / excluded by controlling reason:")
    for category, count in summary["removed_by_category"].items():  # type: ignore[union-attr]
        print(f"  {category}: {count}")
    conflicts = summary["resolved_conflicts"]
    print(f"\nResolved review conflicts: {len(conflicts)}")  # type: ignore[arg-type]
    for conflict in conflicts:  # type: ignore[union-attr]
        print(
            f"  {conflict['group_id']}: {conflict['cross_decision']} overridden by "
            f"{conflict['higher_priority_reason']} for {conflict['selected_file']}"
        )
    print("Review unresolved: 0")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the cleaned eggplant dataset")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy accepted images and write reports (default: dry-run)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    try:
        plan, conflicts, fingerprint = load_and_plan(root)
        summary = build_summary(plan, conflicts, fingerprint)
        existing = existing_cleaned_files(root / "dataset" / "cleaned" / "eggplant")
        if existing:
            raise BuildError(
                f"Cleaned output already contains {len(existing)} file(s); refusing to overwrite"
            )
        print_summary(summary, "APPLY" if args.apply else "DRY RUN")
        if args.apply:
            apply_plan(root, plan, summary)
            print("\nBuild completed. Accepted files were copied from raw to cleaned.")
        else:
            print("\nDry-run only. No cleaned files or reports were written.")
        return 0
    except BuildError as error:
        print(f"BUILD FAILED: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
