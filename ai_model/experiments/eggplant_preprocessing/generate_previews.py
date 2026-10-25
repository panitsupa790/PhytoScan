from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageStat


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = AI_MODEL_ROOT.parent
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from preprocessing.eggplant import VARIANTS, load_config, preprocess_image  # noqa: E402


CLASSES = ("healthy", "leaf_spot", "mosaic_virus")
ALLOWED_SOURCE_SPLITS = ("train", "val")
PREVIEW_PURPOSE = "preview_sanity_check_only"
PREVIEW_MANIFEST_FIELDS = (
    "source_split",
    "class",
    "filename",
    "variant",
    "config_version",
    "seed",
    "purpose",
)
STATISTICS_FIELDS = (
    "source_split",
    "class",
    "filename",
    "variant",
    "width",
    "height",
    "mode",
    "min_pixel",
    "max_pixel",
    "mean_luminance",
    "std_luminance",
    "laplacian_variance",
    "output_rgb_sha256",
)


class PreviewError(RuntimeError):
    pass


def read_split_manifest(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise PreviewError(f"Split manifest is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {"class", "filename", "sha256", "split", "seed"}
        missing = sorted(required - set(reader.fieldnames or ()))
        if missing:
            raise PreviewError(f"Split manifest is missing columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def select_preview_samples(
    rows: list[dict[str, str]],
    source_split: str = "train",
    per_class: int = 5,
    seed: int = 42,
) -> list[dict[str, str]]:
    if source_split not in ALLOWED_SOURCE_SPLITS:
        raise PreviewError(
            f"Preview source must be train or val; {source_split!r} is forbidden"
        )
    if per_class <= 0:
        raise PreviewError("per_class must be positive")
    rng = random.Random(seed)
    selected: list[dict[str, str]] = []
    for class_name in CLASSES:
        candidates = sorted(
            (
                row
                for row in rows
                if row["split"] == source_split and row["class"] == class_name
            ),
            key=lambda row: (row["filename"].casefold(), row["filename"]),
        )
        if len(candidates) < per_class:
            raise PreviewError(
                f"Not enough {source_split} images for {class_name}: {len(candidates)}"
            )
        selected.extend(rng.sample(candidates, per_class))
    return selected


def laplacian_variance(image: Image.Image) -> float:
    grayscale = image.convert("L")
    width, height = grayscale.size
    pixels = grayscale.load()
    count = max(0, (width - 2) * (height - 2))
    if count == 0:
        return 0.0
    total = 0.0
    total_squared = 0.0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            value = (
                pixels[x - 1, y]
                + pixels[x + 1, y]
                + pixels[x, y - 1]
                + pixels[x, y + 1]
                - 4 * pixels[x, y]
            )
            total += value
            total_squared += value * value
    mean = total / count
    return total_squared / count - mean * mean


def image_statistics(
    image: Image.Image,
    source_row: dict[str, str],
    variant: str,
) -> dict[str, object]:
    luminance = image.convert("L")
    luminance_stats = ImageStat.Stat(luminance)
    extrema = image.getextrema()
    return {
        "source_split": source_row["split"],
        "class": source_row["class"],
        "filename": source_row["filename"],
        "variant": variant,
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "min_pixel": min(channel[0] for channel in extrema),
        "max_pixel": max(channel[1] for channel in extrema),
        "mean_luminance": f"{luminance_stats.mean[0]:.6f}",
        "std_luminance": f"{luminance_stats.stddev[0]:.6f}",
        "laplacian_variance": f"{laplacian_variance(image):.6f}",
        "output_rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
    }


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        ("arialbd.ttf", "DejaVuSans-Bold.ttf")
        if bold
        else ("arial.ttf", "DejaVuSans.ttf")
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def abbreviated_filename(filename: str, limit: int = 31) -> str:
    return filename if len(filename) <= limit else f"{filename[: limit - 3]}..."


def variant_label(variant: str, config: dict[str, Any]) -> str:
    if variant == "P0":
        return "P0 resize + pad"
    parameters = config["variants"][variant]["parameters"]
    if variant == "P1":
        return f"P1 median {parameters['size']}x{parameters['size']}"
    if variant == "P2":
        return f"P2 luminance B{parameters['brightness_factor']} C{parameters['contrast_factor']}"
    return (
        f"P3 unsharp r{parameters['radius']} p{parameters['percent']} "
        f"t{parameters['threshold']}"
    )


def render_contact_sheet(
    class_name: str,
    samples: list[dict[str, str]],
    rendered: dict[tuple[str, str, str], Image.Image],
    config: dict[str, Any],
    output_path: Path,
) -> None:
    tile_size = (config["output"]["target_width"], config["output"]["target_height"])
    columns = ("Original", *VARIANTS)
    margin = 24
    gap = 12
    header_height = 96
    label_height = 46
    sheet_width = margin * 2 + len(columns) * tile_size[0] + (len(columns) - 1) * gap
    sheet_height = header_height + len(samples) * (tile_size[1] + label_height + gap) + margin
    sheet = Image.new("RGB", (sheet_width, sheet_height), (246, 248, 246))
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(24, bold=True)
    label_font = load_font(15, bold=True)
    detail_font = load_font(13)
    draw.text((margin, 18), f"Eggplant preprocessing sanity check: {class_name}", fill=(23, 62, 42), font=title_font)

    for column_index, column in enumerate(columns):
        x = margin + column_index * (tile_size[0] + gap)
        label = "Original display" if column == "Original" else variant_label(column, config)
        draw.text((x, 58), label, fill=(28, 45, 35), font=label_font)

    for row_index, source_row in enumerate(samples):
        y = header_height + row_index * (tile_size[1] + label_height + gap)
        original = rendered[(source_row["class"], source_row["filename"], "P0")]
        row_images = (
            original,
            *(
                rendered[(source_row["class"], source_row["filename"], variant)]
                for variant in VARIANTS
            ),
        )
        for column_index, image in enumerate(row_images):
            x = margin + column_index * (tile_size[0] + gap)
            sheet.paste(image, (x, y))
            draw.rectangle(
                (x, y, x + tile_size[0] - 1, y + tile_size[1] - 1),
                outline=(174, 184, 177),
                width=1,
            )
        draw.text(
            (margin, y + tile_size[1] + 7),
            abbreviated_filename(source_row["filename"]),
            fill=(36, 49, 41),
            font=detail_font,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="JPEG", quality=92, optimize=True)


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def aggregate_statistics(rows: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for variant in VARIANTS:
        selected = [row for row in rows if row["variant"] == variant]
        result[variant] = {
            "samples": len(selected),
            "mean_luminance": sum(float(row["mean_luminance"]) for row in selected) / len(selected),
            "mean_std_luminance": sum(float(row["std_luminance"]) for row in selected) / len(selected),
            "mean_laplacian_variance": sum(float(row["laplacian_variance"]) for row in selected) / len(selected),
            "minimum_pixel": min(int(row["min_pixel"]) for row in selected),
            "maximum_pixel": max(int(row["max_pixel"]) for row in selected),
        }
    return result


def generate(source_split: str = "train", per_class: int = 5) -> dict[str, object]:
    config = load_config()
    seed = int(config["random_seed"])
    experiment_root = AI_MODEL_ROOT / "experiments" / "eggplant_preprocessing"
    preview_root = experiment_root / "previews"
    manifest_path = experiment_root / "preprocessing_manifest.csv"
    statistics_path = experiment_root / "preprocessing_statistics.csv"
    summary_path = experiment_root / "preprocessing_summary.json"
    existing = [
        path
        for path in (manifest_path, statistics_path, summary_path)
        if path.exists()
    ] + ([path for path in preview_root.rglob("*") if path.is_file()] if preview_root.exists() else [])
    if existing:
        raise PreviewError("Preview outputs already exist; refusing to overwrite")

    split_manifest = read_split_manifest(
        PROJECT_ROOT / "dataset" / "metadata" / "eggplant_split_manifest.csv"
    )
    samples = select_preview_samples(split_manifest, source_split, per_class, seed)
    if any(row["split"] == "test" for row in samples):
        raise PreviewError("Test-set image selected for preview")

    manifest_rows: list[dict[str, object]] = []
    statistics_rows: list[dict[str, object]] = []
    rendered: dict[tuple[str, str, str], Image.Image] = {}
    split_root = PROJECT_ROOT / "dataset" / "split" / "eggplant"
    for source_row in samples:
        source_path = split_root / source_row["split"] / source_row["class"] / source_row["filename"]
        if hashlib.sha256(source_path.read_bytes()).hexdigest() != source_row["sha256"]:
            raise PreviewError(f"Source hash mismatch: {source_path}")
        for variant in VARIANTS:
            output = preprocess_image(source_path, variant, config)
            rendered[(source_row["class"], source_row["filename"], variant)] = output
            manifest_rows.append(
                {
                    "source_split": source_row["split"],
                    "class": source_row["class"],
                    "filename": source_row["filename"],
                    "variant": variant,
                    "config_version": config["config_version"],
                    "seed": seed,
                    "purpose": PREVIEW_PURPOSE,
                }
            )
            statistics_rows.append(image_statistics(output, source_row, variant))

    for class_name in CLASSES:
        class_samples = [row for row in samples if row["class"] == class_name]
        render_contact_sheet(
            class_name,
            class_samples,
            rendered,
            config,
            preview_root / f"{class_name}_comparison.jpg",
        )

    write_csv(manifest_path, PREVIEW_MANIFEST_FIELDS, manifest_rows)
    write_csv(statistics_path, STATISTICS_FIELDS, statistics_rows)
    summary: dict[str, object] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_version": config["config_version"],
        "seed": seed,
        "source_split": source_split,
        "test_images_used": 0,
        "images_per_class": per_class,
        "source_image_count": len(samples),
        "variant_output_count": len(manifest_rows),
        "class_counts": dict(Counter(row["class"] for row in samples)),
        "variants": list(VARIANTS),
        "statistics_by_variant": aggregate_statistics(statistics_rows),
        "purpose": PREVIEW_PURPOSE,
        "classification_performance_claim": False,
        "winner_selected": False,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic preprocessing previews")
    parser.add_argument(
        "--source-split",
        choices=ALLOWED_SOURCE_SPLITS,
        default="train",
        help="Source split for visual sanity samples (test is intentionally unavailable)",
    )
    parser.add_argument("--per-class", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = generate(args.source_split, args.per_class)
    except PreviewError as error:
        print(f"PREVIEW GENERATION FAILED: {error}")
        return 1
    print("Preprocessing preview generation completed")
    print(f"Source split: {summary['source_split']}")
    print(f"Source images: {summary['source_image_count']}")
    print(f"Variant outputs evaluated in memory: {summary['variant_output_count']}")
    print(f"Test images used: {summary['test_images_used']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
