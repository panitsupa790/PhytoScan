from __future__ import annotations

import csv
import hashlib
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


CLASSES = ("healthy", "leaf_spot", "mosaic_virus")
RANDOM_SEED = 42
RANDOM_IMAGES_PER_CLASS = 50
IMAGES_PER_SHEET = 10
HASH_CHUNK_SIZE = 1024 * 1024

CROSS_CLASS_FIELDS = (
    "group_id",
    "sha256",
    "class_a",
    "filename_a",
    "class_b",
    "filename_b",
    "decision",
    "reviewer",
    "notes",
)
RESOLUTION_FIELDS = (
    "class",
    "filename",
    "width",
    "height",
    "decision",
    "reviewer",
    "notes",
)
RANDOM_AUDIT_FIELDS = (
    "class",
    "filename",
    "review_status",
    "reviewer",
    "notes",
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as image_file:
        for chunk in iter(lambda: image_file.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        ("DejaVuSans-Bold.ttf", "arialbd.ttf")
        if bold
        else ("DejaVuSans.ttf", "arial.ttf")
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def image_path(raw_root: Path, class_name: str, filename: str) -> Path:
    path = (raw_root / class_name / filename).resolve()
    if not path.is_relative_to(raw_root.resolve()):
        raise ValueError(f"Unsafe image path in report: {class_name}/{filename}")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def verify_raw_matches_validation(
    validation_rows: list[dict[str, str]], raw_root: Path
) -> int:
    expected_paths: set[Path] = set()
    for row in validation_rows:
        if row["status"] != "valid":
            raise ValueError(
                f"Validation report contains a non-valid image: "
                f"{row['class']}/{row['filename']}"
            )
        path = image_path(raw_root, row["class"], row["filename"])
        expected_paths.add(path)
        actual_hash = sha256_file(path)
        if actual_hash != row["sha256"]:
            raise ValueError(f"Raw image changed since validation: {path}")

    actual_paths = {
        path.resolve()
        for class_name in CLASSES
        for path in (raw_root / class_name).rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    }
    if actual_paths != expected_paths:
        missing = len(expected_paths - actual_paths)
        unexpected = len(actual_paths - expected_paths)
        raise ValueError(
            f"Raw file set differs from validation report: "
            f"missing={missing}, unexpected={unexpected}"
        )
    if len(expected_paths) != 3415:
        raise ValueError(f"Expected 3415 validated raw images, found {len(expected_paths)}")
    return len(expected_paths)


def paste_image(canvas: Image.Image, path: Path, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((right - left, bottom - top), Image.Resampling.LANCZOS)
        x = left + (right - left - image.width) // 2
        y = top + (bottom - top - image.height) // 2
        canvas.paste(image, (x, y))


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    fill: str = "#17251c",
    line_gap: int = 5,
) -> int:
    x, y = position
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    line_height = draw.textbbox((0, 0), "Ag", font=font)[3] + line_gap
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def save_cross_class_sheet(
    output_path: Path,
    group_id: str,
    image_hash: str,
    rows: list[dict[str, str]],
    raw_root: Path,
) -> None:
    canvas = Image.new("RGB", (1400, 1100), "#f5f7f3")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(42, bold=True)
    body_font = load_font(28)
    label_font = load_font(30, bold=True)

    draw.text((60, 45), f"Cross-class duplicate {group_id}", font=title_font, fill="#173e2a")
    draw.text((60, 105), f"SHA-256: {image_hash[:16]}...", font=body_font, fill="#44534a")
    draw.rounded_rectangle((60, 160, 1340, 820), radius=8, outline="#809187", width=3, fill="white")
    paste_image(
        canvas,
        image_path(raw_root, rows[0]["class"], rows[0]["filename"]),
        (85, 180, 1315, 800),
    )

    y = 850
    for index, row in enumerate(rows, start=1):
        draw.text((60, y), f"File {index} [{row['class']}]", font=label_font, fill="#173e2a")
        y = draw_wrapped_text(
            draw,
            (350, y),
            row["filename"],
            body_font,
            max_width=980,
        )
        y += 10

    canvas.save(output_path, format="JPEG", quality=90, optimize=True)


def save_grid_sheet(
    output_path: Path,
    title: str,
    rows: list[dict[str, str]],
    raw_root: Path,
    include_class: bool,
) -> None:
    columns = 2
    rows_per_sheet = 5
    canvas = Image.new("RGB", (1600, 2150), "#f5f7f3")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(40, bold=True)
    label_font = load_font(22, bold=True)
    filename_font = load_font(20)

    draw.text((45, 35), title, font=title_font, fill="#173e2a")
    cell_width = 750
    cell_height = 390
    start_y = 120
    gap_x = 30
    gap_y = 15

    for index, row in enumerate(rows):
        grid_row, grid_column = divmod(index, columns)
        if grid_row >= rows_per_sheet:
            raise ValueError("Too many images for one contact sheet")
        left = 35 + grid_column * (cell_width + gap_x)
        top = start_y + grid_row * (cell_height + gap_y)
        right = left + cell_width
        bottom = top + cell_height
        draw.rounded_rectangle((left, top, right, bottom), radius=8, outline="#9aaa9f", width=2, fill="white")
        paste_image(
            canvas,
            image_path(raw_root, row["class"], row["filename"]),
            (left + 15, top + 15, right - 15, bottom - 75),
        )
        label = f"[{row['class']}]" if include_class else row["class"]
        draw.text((left + 15, bottom - 65), label, font=label_font, fill="#173e2a")
        draw_wrapped_text(
            draw,
            (left + 180, bottom - 65),
            row["filename"],
            filename_font,
            max_width=cell_width - 205,
            line_gap=2,
        )

    canvas.save(output_path, format="JPEG", quality=88, optimize=True)


def preserved_review_values(
    path: Path,
    key_fields: tuple[str, ...],
    editable_fields: tuple[str, ...],
) -> dict[tuple[str, ...], dict[str, str]]:
    if not path.exists():
        return {}
    preserved: dict[tuple[str, ...], dict[str, str]] = {}
    for row in read_csv(path):
        key = tuple(row[field] for field in key_fields)
        preserved[key] = {field: row.get(field, "") for field in editable_fields}
    return preserved


def write_review_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: list[dict[str, str]],
    key_fields: tuple[str, ...],
    editable_fields: tuple[str, ...],
) -> None:
    existing = preserved_review_values(path, key_fields, editable_fields)
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        if key in existing:
            row.update(existing[key])

    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_cross_class_review(
    duplicate_rows: list[dict[str, str]],
    raw_root: Path,
    review_dir: Path,
    metadata_dir: Path,
) -> tuple[int, int]:
    rows_by_hash: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in duplicate_rows:
        if row["duplicate_type"] == "cross_class":
            rows_by_hash[row["sha256"]].append(row)

    if len(rows_by_hash) != 48:
        raise ValueError(f"Expected 48 cross-class groups, found {len(rows_by_hash)}")

    csv_rows: list[dict[str, str]] = []
    for number, image_hash in enumerate(sorted(rows_by_hash), start=1):
        rows = sorted(rows_by_hash[image_hash], key=lambda row: (row["class"], row["filename"]))
        if len(rows) != 2 or len({row["class"] for row in rows}) != 2:
            raise ValueError(f"Cross-class group {image_hash} is not a two-file cross-class pair")
        group_id = f"group_{number:03d}"
        save_cross_class_sheet(review_dir / f"{group_id}.jpg", group_id, image_hash, rows, raw_root)
        csv_rows.append(
            {
                "group_id": group_id,
                "sha256": image_hash,
                "class_a": rows[0]["class"],
                "filename_a": rows[0]["filename"],
                "class_b": rows[1]["class"],
                "filename_b": rows[1]["filename"],
                "decision": "",
                "reviewer": "",
                "notes": "",
            }
        )

    write_review_csv(
        metadata_dir / "eggplant_cross_class_review.csv",
        CROSS_CLASS_FIELDS,
        csv_rows,
        key_fields=("sha256",),
        editable_fields=("decision", "reviewer", "notes"),
    )
    return len(csv_rows), len(csv_rows)


def build_resolution_review(
    validation_rows: list[dict[str, str]],
    raw_root: Path,
    review_dir: Path,
    metadata_dir: Path,
) -> tuple[int, int]:
    rows = sorted(
        (
            row
            for row in validation_rows
            if row["class"] == "mosaic_virus" and row["width"] == "256" and row["height"] == "256"
        ),
        key=lambda row: row["filename"].casefold(),
    )
    if len(rows) != 20:
        raise ValueError(f"Expected 20 mosaic_virus 256x256 images, found {len(rows)}")

    for sheet_number, offset in enumerate(range(0, len(rows), IMAGES_PER_SHEET), start=1):
        save_grid_sheet(
            review_dir / f"sheet_{sheet_number:02d}.jpg",
            f"Mosaic virus 256x256 review - sheet {sheet_number}",
            rows[offset : offset + IMAGES_PER_SHEET],
            raw_root,
            include_class=False,
        )

    csv_rows = [
        {
            "class": row["class"],
            "filename": row["filename"],
            "width": row["width"],
            "height": row["height"],
            "decision": "",
            "reviewer": "",
            "notes": "",
        }
        for row in rows
    ]
    write_review_csv(
        metadata_dir / "eggplant_resolution_review.csv",
        RESOLUTION_FIELDS,
        csv_rows,
        key_fields=("class", "filename"),
        editable_fields=("decision", "reviewer", "notes"),
    )
    sheet_count = (len(rows) + IMAGES_PER_SHEET - 1) // IMAGES_PER_SHEET
    return len(rows), sheet_count


def build_random_audit(
    validation_rows: list[dict[str, str]],
    raw_root: Path,
    review_dir: Path,
    metadata_dir: Path,
) -> tuple[dict[str, int], int]:
    rows_by_class: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in validation_rows:
        if row["status"] == "valid" and row["class"] in CLASSES:
            rows_by_class[row["class"]].append(row)

    rng = random.Random(RANDOM_SEED)
    selected: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    sheet_count = 0
    for class_name in CLASSES:
        candidates = sorted(rows_by_class[class_name], key=lambda row: row["filename"].casefold())
        if len(candidates) < RANDOM_IMAGES_PER_CLASS:
            raise ValueError(f"Not enough {class_name} images for random audit")
        sample = sorted(
            rng.sample(candidates, RANDOM_IMAGES_PER_CLASS),
            key=lambda row: row["filename"].casefold(),
        )
        if len({row["filename"] for row in sample}) != RANDOM_IMAGES_PER_CLASS:
            raise ValueError(f"Duplicate file path in {class_name} random sample")
        counts[class_name] = len(sample)
        selected.extend(sample)

        for class_sheet, offset in enumerate(range(0, len(sample), IMAGES_PER_SHEET), start=1):
            save_grid_sheet(
                review_dir / f"{class_name}_sheet_{class_sheet:02d}.jpg",
                f"Random audit: {class_name} - sheet {class_sheet}",
                sample[offset : offset + IMAGES_PER_SHEET],
                raw_root,
                include_class=True,
            )
            sheet_count += 1

    csv_rows = [
        {
            "class": row["class"],
            "filename": row["filename"],
            "review_status": "",
            "reviewer": "",
            "notes": "",
        }
        for row in selected
    ]
    write_review_csv(
        metadata_dir / "eggplant_random_audit.csv",
        RANDOM_AUDIT_FIELDS,
        csv_rows,
        key_fields=("class", "filename"),
        editable_fields=("review_status", "reviewer", "notes"),
    )
    return counts, sheet_count


def main() -> int:
    root = project_root()
    dataset_dir = root / "dataset"
    raw_root = dataset_dir / "raw" / "eggplant"
    metadata_dir = dataset_dir / "metadata"
    review_dir = dataset_dir / "review"
    cross_class_dir = review_dir / "cross_class"
    resolution_dir = review_dir / "resolution_256"
    random_audit_dir = review_dir / "random_audit"

    for directory in (cross_class_dir, resolution_dir, random_audit_dir):
        directory.mkdir(parents=True, exist_ok=True)

    validation_rows = read_csv(metadata_dir / "eggplant_validation.csv")
    duplicate_rows = read_csv(metadata_dir / "eggplant_duplicates.csv")
    verified_raw_images = verify_raw_matches_validation(validation_rows, raw_root)

    cross_groups, cross_sheets = build_cross_class_review(
        duplicate_rows, raw_root, cross_class_dir, metadata_dir
    )
    resolution_images, resolution_sheets = build_resolution_review(
        validation_rows, raw_root, resolution_dir, metadata_dir
    )
    random_counts, random_sheets = build_random_audit(
        validation_rows, raw_root, random_audit_dir, metadata_dir
    )

    print("Review materials generated")
    print(f"Raw SHA-256 verified images: {verified_raw_images}")
    print(f"Cross-class groups: {cross_groups}")
    print(f"Cross-class sheets: {cross_sheets}")
    print(f"Resolution 256x256 images: {resolution_images}")
    print(f"Resolution sheets: {resolution_sheets}")
    for class_name in CLASSES:
        print(f"Random audit {class_name}: {random_counts[class_name]}")
    print(f"Random audit total: {sum(random_counts.values())}")
    print(f"Random audit sheets: {random_sheets}")
    print(f"Random seed: {RANDOM_SEED}")
    print("Review decisions were not generated. Human review is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
