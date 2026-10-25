from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image


CLASSES = ("healthy", "leaf_spot", "mosaic_virus")
EXPECTED_COUNTS = {
    "healthy": 1451,
    "leaf_spot": 602,
    "mosaic_virus": 1362,
}
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VALIDATION_FIELDS = (
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
DUPLICATE_FIELDS = ("sha256", "duplicate_type", "class", "filename")
HASH_CHUNK_SIZE = 1024 * 1024


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as image_file:
        for chunk in iter(lambda: image_file.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def validate_image(path: Path, class_name: str, class_dir: Path) -> dict[str, object]:
    extension = path.suffix.lower()
    row: dict[str, object] = {
        "class": class_name,
        "filename": path.relative_to(class_dir).as_posix(),
        "extension": extension,
        "width": "",
        "height": "",
        "mode": "",
        "sha256": "",
        "status": "invalid",
        "error": "",
    }

    if extension not in SUPPORTED_EXTENSIONS:
        row["status"] = "unsupported_extension"
        row["error"] = f"Unsupported extension: {extension or '<none>'}"
        return row

    try:
        with Image.open(path) as image:
            row["width"], row["height"] = image.size
            row["mode"] = image.mode
            image.verify()
        row["sha256"] = sha256_file(path)
        row["status"] = "valid"
    except Exception as error:
        row["error"] = f"{type(error).__name__}: {error}"

    return row


def duplicate_rows(
    validation_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int, int, int]:
    rows_by_hash: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in validation_rows:
        if row["status"] == "valid" and row["sha256"]:
            rows_by_hash[str(row["sha256"])].append(row)

    report_rows: list[dict[str, object]] = []
    duplicate_group_count = 0
    same_class_group_count = 0
    cross_class_group_count = 0

    for image_hash, rows in sorted(rows_by_hash.items()):
        if len(rows) < 2:
            continue

        duplicate_group_count += 1
        classes = {str(row["class"]) for row in rows}
        duplicate_type = "same_class" if len(classes) == 1 else "cross_class"
        if duplicate_type == "same_class":
            same_class_group_count += 1
        else:
            cross_class_group_count += 1

        for row in sorted(rows, key=lambda item: (str(item["class"]), str(item["filename"]))):
            report_rows.append(
                {
                    "sha256": image_hash,
                    "duplicate_type": duplicate_type,
                    "class": row["class"],
                    "filename": row["filename"],
                }
            )

    return (
        report_rows,
        duplicate_group_count,
        same_class_group_count,
        cross_class_group_count,
    )


def print_summary(
    validation_rows: list[dict[str, object]],
    class_counts: Counter[str],
    extension_counts: Counter[str],
    missing_classes: list[str],
    unknown_extensions: Counter[str],
    duplicate_counts: tuple[int, int, int],
    report_paths: tuple[Path, Path],
    root: Path,
) -> None:
    valid_rows = [row for row in validation_rows if row["status"] == "valid"]
    invalid_rows = [row for row in validation_rows if row["status"] != "valid"]
    widths = [int(row["width"]) for row in valid_rows]
    heights = [int(row["height"]) for row in valid_rows]
    resolutions = Counter((int(row["width"]), int(row["height"])) for row in valid_rows)
    modes = Counter(str(row["mode"]) for row in valid_rows)

    print("Dataset validation summary")
    print()
    for class_name in CLASSES:
        count = class_counts[class_name]
        expected = EXPECTED_COUNTS[class_name]
        marker = "" if count == expected else f" (expected {expected})"
        print(f"{class_name}: {count}{marker}")
    print()
    print(f"Total images: {len(validation_rows)}")
    print(f"Valid images: {len(valid_rows)}")
    print(f"Invalid images: {len(invalid_rows)}")

    print("\nExtensions:")
    for extension, count in sorted(extension_counts.items()):
        print(f"{extension or '<none>'}: {count}")
    if unknown_extensions:
        print("Unknown extensions:")
        for extension, count in sorted(unknown_extensions.items()):
            print(f"  {extension or '<none>'}: {count}")
    if missing_classes:
        print(f"Missing class directories: {', '.join(missing_classes)}")

    duplicate_groups, same_class_groups, cross_class_groups = duplicate_counts
    print("\nExact duplicates:")
    print(f"Duplicate groups: {duplicate_groups}")
    print(f"Same-class duplicate groups: {same_class_groups}")
    print(f"Cross-class duplicate groups: {cross_class_groups}")

    print("\nResolution:")
    if valid_rows:
        print(f"Width min/max: {min(widths)} / {max(widths)}")
        print(f"Height min/max: {min(heights)} / {max(heights)}")
        print(f"Unique resolutions: {len(resolutions)}")
        print("Most common resolutions:")
        for (width, height), count in resolutions.most_common(10):
            print(f"  {width}x{height}: {count}")
        print("Image modes:")
        for mode, count in sorted(modes.items()):
            print(f"  {mode}: {count}")
    else:
        print("No valid images available for dimension statistics.")

    if invalid_rows:
        print("\nInvalid or unsupported files:")
        for row in invalid_rows:
            print(f"  {row['class']}/{row['filename']}: {row['error']}")

    print("\nReports:")
    for report_path in report_paths:
        print(report_path.relative_to(root).as_posix())


def main() -> int:
    root = project_root()
    raw_root = root / "dataset" / "raw" / "eggplant"
    metadata_root = root / "dataset" / "metadata"
    validation_report = metadata_root / "eggplant_validation.csv"
    duplicate_report = metadata_root / "eggplant_duplicates.csv"

    validation_rows: list[dict[str, object]] = []
    class_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    unknown_extensions: Counter[str] = Counter()
    missing_classes: list[str] = []

    for class_name in CLASSES:
        class_dir = raw_root / class_name
        if not class_dir.is_dir():
            missing_classes.append(class_name)
            continue

        files = sorted(
            (
                path
                for path in class_dir.rglob("*")
                if path.is_file() and path.name != ".gitkeep"
            ),
            key=lambda path: path.relative_to(class_dir).as_posix().casefold(),
        )
        class_counts[class_name] = len(files)

        for path in files:
            extension = path.suffix.lower()
            extension_counts[extension] += 1
            if extension not in SUPPORTED_EXTENSIONS:
                unknown_extensions[extension] += 1
            validation_rows.append(validate_image(path, class_name, class_dir))

    duplicates, duplicate_groups, same_class_groups, cross_class_groups = duplicate_rows(
        validation_rows
    )
    write_csv(validation_report, VALIDATION_FIELDS, validation_rows)
    write_csv(duplicate_report, DUPLICATE_FIELDS, duplicates)
    print_summary(
        validation_rows=validation_rows,
        class_counts=class_counts,
        extension_counts=extension_counts,
        missing_classes=missing_classes,
        unknown_extensions=unknown_extensions,
        duplicate_counts=(duplicate_groups, same_class_groups, cross_class_groups),
        report_paths=(validation_report, duplicate_report),
        root=root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
