from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from phyto_fasttrack.core import CLASS_NAMES, sha256_file, utc_now, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only Marigold-to-Rose targeted error analysis")
    parser.add_argument("--fresh-model", required=True, type=Path)
    parser.add_argument("--v5-model", required=True, type=Path)
    parser.add_argument("--known-manifest", required=True, type=Path)
    parser.add_argument("--train-manifest", required=True, type=Path)
    parser.add_argument("--debug-predictions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20261030)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def preprocess_tensorflow(path: Path):
    import tensorflow as tf

    encoded = tf.io.read_file(str(path))
    image = tf.io.decode_image(encoded, channels=3, expand_animations=False)
    image = tf.cast(image, tf.float32)
    image = tf.image.resize(image, (224, 224), method="bilinear", antialias=False)
    return tf.expand_dims(image, 0)


def predict(model, path: Path) -> np.ndarray:
    values = model(preprocess_tensorflow(path), training=False)
    return np.asarray(values, dtype=np.float32)[0]


def gradcam(model, path: Path, class_index: int) -> np.ndarray:
    import tensorflow as tf

    backbone = model.get_layer("efficientnetb0")
    backbone_index = model.layers.index(backbone)
    last_conv = backbone.get_layer("top_conv")
    feature_model = tf.keras.Model(backbone.input, (last_conv.output, backbone.output))
    batch = preprocess_tensorflow(path)
    with tf.GradientTape() as tape:
        values = batch
        for layer in model.layers[1:backbone_index]:
            values = layer(values, training=False)
        conv_features, values = feature_model(values, training=False)
        for layer in model.layers[backbone_index + 1 :]:
            values = layer(values, training=False)
        score = tf.cast(values[:, class_index], tf.float32)
    gradients = tape.gradient(score, conv_features)
    if gradients is None:
        raise RuntimeError("Grad-CAM gradient is unavailable for top_conv")
    weights = tf.reduce_mean(tf.cast(gradients, tf.float32), axis=(1, 2))
    heatmap = tf.reduce_sum(tf.cast(conv_features, tf.float32) * weights[:, None, None, :], axis=-1)[0]
    heatmap = tf.nn.relu(heatmap)
    maximum = tf.reduce_max(heatmap)
    if float(maximum) > 0:
        heatmap = heatmap / maximum
    return np.asarray(heatmap, dtype=np.float32)


def _font(size: int):
    candidates = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        image = source.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def overlay_heatmap(path: Path, heatmap: np.ndarray, alpha: float = 0.45) -> Image.Image:
    original = _fit_image(path, (448, 448))
    heat = cv2.resize(heatmap, original.size, interpolation=cv2.INTER_CUBIC)
    coloured = cv2.applyColorMap(np.uint8(np.clip(heat, 0, 1) * 255), cv2.COLORMAP_JET)
    coloured = cv2.cvtColor(coloured, cv2.COLOR_BGR2RGB)
    overlay = (np.asarray(original, dtype=np.float32) * (1 - alpha) + coloured.astype(np.float32) * alpha)
    return Image.fromarray(np.uint8(np.clip(overlay, 0, 255)))


def gradcam_figure(
    image_path: Path,
    model_name: str,
    probabilities: np.ndarray,
    rose_heatmap: np.ndarray,
    marigold_heatmap: np.ndarray,
    output_path: Path,
) -> None:
    width, height = 3 * 448, 530
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    title_font, label_font = _font(22), _font(17)
    panels = (
        (_fit_image(image_path, (448, 448)), "Original known Marigold"),
        (overlay_heatmap(image_path, rose_heatmap), f"Grad-CAM target Rose: {probabilities[3]:.4%}"),
        (overlay_heatmap(image_path, marigold_heatmap), f"Grad-CAM target Marigold: {probabilities[1]:.4%}"),
    )
    draw.text((18, 8), f"{model_name} — top_conv Grad-CAM (interpretive, not causal proof)", fill="black", font=title_font)
    for index, (panel, label) in enumerate(panels):
        x = index * 448
        canvas.paste(panel, (x, 45))
        draw.text((x + 10, 498), label, fill="black", font=label_font)
    canvas.save(output_path, quality=95)


def gradcam_comparison(v5_path: Path, fresh_path: Path, output_path: Path) -> None:
    v5 = Image.open(v5_path).convert("RGB")
    fresh = Image.open(fresh_path).convert("RGB")
    canvas = Image.new("RGB", (max(v5.width, fresh.width), v5.height + fresh.height), "white")
    canvas.paste(v5, (0, 0))
    canvas.paste(fresh, (0, v5.height))
    canvas.save(output_path, quality=95)


def rough_foreground_mask(path: Path, shape: tuple[int, int]) -> tuple[np.ndarray, float, bool]:
    with Image.open(path) as source:
        rgb = np.asarray(source.convert("RGB"))
    border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]), axis=0)
    border_colour = np.median(border.astype(np.float32), axis=0)
    distance = np.linalg.norm(rgb.astype(np.float32) - border_colour, axis=2)
    mask = (distance >= 28).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    coverage = float(mask.mean())
    reliable = 0.03 <= coverage <= 0.80
    resized = cv2.resize(mask, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
    return resized, coverage, reliable


def attention_metrics(path: Path, heatmap: np.ndarray) -> dict[str, Any]:
    total = float(heatmap.sum())
    mask, coverage, reliable = rough_foreground_mask(path, heatmap.shape)
    foreground_mass = float(heatmap[mask].sum() / total) if reliable and total > 0 else None
    height, width = heatmap.shape
    border = np.ones_like(heatmap, dtype=bool)
    y0, y1 = round(height * 0.2), round(height * 0.8)
    x0, x1 = round(width * 0.2), round(width * 0.8)
    border[y0:y1, x0:x1] = False
    return {
        "rough_foreground_coverage": coverage,
        "rough_foreground_mask_reliable": reliable,
        "gradcam_mass_inside_rough_foreground": foreground_mass,
        "gradcam_mass_in_outer_20_percent_frame": float(heatmap[border].sum() / total) if total > 0 else None,
        "heatmap_grid": list(heatmap.shape),
    }


def deterministic_stratified_sample(
    rows: Sequence[dict[str, str]], plant: str, count: int, seed: int
) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["plant"] == plant:
            grouped[row.get("source", "unknown")].append(row)
    for source_rows in grouped.values():
        source_rows.sort(
            key=lambda row: hashlib.sha256(f"{seed}|{row['path']}".encode("utf-8")).hexdigest()
        )
    sources = sorted(grouped)
    selected: list[dict[str, str]] = []
    offset = 0
    while len(selected) < count:
        changed = False
        for source in sources:
            if offset < len(grouped[source]):
                selected.append(grouped[source][offset])
                changed = True
                if len(selected) == count:
                    break
        if not changed:
            break
        offset += 1
    return selected


def contact_sheet(
    rows: Sequence[dict[str, Any]], output_path: Path, title: str, columns: int = 4
) -> None:
    tile_width, image_height, caption_height = 270, 210, 78
    rows_count = max(1, math.ceil(len(rows) / columns))
    title_height = 52
    canvas = Image.new("RGB", (columns * tile_width, title_height + rows_count * (image_height + caption_height)), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((14, 10), title, fill="black", font=_font(24))
    caption_font = _font(13)
    for index, row in enumerate(rows):
        x = (index % columns) * tile_width
        y = title_height + (index // columns) * (image_height + caption_height)
        panel = _fit_image(Path(row["path"]), (tile_width, image_height))
        canvas.paste(panel, (x, y))
        caption = str(row.get("caption") or f"{row.get('plant', '')} | {row.get('source', '')}\n{Path(row['path']).name}")
        draw.multiline_text((x + 6, y + image_height + 5), caption[:180], fill="black", font=caption_font, spacing=2)
    canvas.save(output_path, quality=92)


def image_background_stats(path: Path) -> dict[str, float]:
    with Image.open(path) as source:
        rgb = np.asarray(source.convert("RGB").resize((96, 96), Image.Resampling.BILINEAR), dtype=np.float32)
    gray = rgb.mean(axis=2)
    patch = 10
    corners = np.concatenate(
        (
            gray[:patch, :patch].ravel(), gray[:patch, -patch:].ravel(),
            gray[-patch:, :patch].ravel(), gray[-patch:, -patch:].ravel(),
        )
    )
    return {
        "mean_brightness": float(gray.mean()),
        "corner_brightness": float(corners.mean()),
        "corner_std": float(corners.std()),
        "near_black_corner_fraction": float((corners <= 20).mean()),
        "near_white_corner_fraction": float((corners >= 235).mean()),
    }


def summarise(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=np.float32)
    return {
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "p10": float(np.quantile(array, 0.10)),
        "p90": float(np.quantile(array, 0.90)),
    }


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise SystemExit(f"Refusing to overwrite output directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    import tensorflow as tf

    tf.keras.mixed_precision.set_global_policy("float32")
    models = {
        "v5": tf.keras.models.load_model(args.v5_model, compile=False),
        "fresh_b0_run08": tf.keras.models.load_model(args.fresh_model, compile=False),
    }
    known_rows = read_csv(args.known_manifest)
    prediction_rows: list[dict[str, Any]] = []
    probability_cache: dict[tuple[str, str], np.ndarray] = {}
    for model_name, model in models.items():
        for row in known_rows:
            path = Path(row["path"])
            probabilities = predict(model, path)
            probability_cache[(model_name, row["plant"])] = probabilities
            order = np.argsort(probabilities)[::-1]
            prediction_rows.append(
                {
                    "model": model_name,
                    "path": str(path),
                    "true_plant": row["plant"],
                    "predicted_plant": CLASS_NAMES[int(order[0])],
                    "top1_confidence": float(probabilities[order[0]]),
                    "top2_plant": CLASS_NAMES[int(order[1])],
                    "top2_confidence": float(probabilities[order[1]]),
                    "margin": float(probabilities[order[0]] - probabilities[order[1]]),
                    **{f"p_{plant}": float(probabilities[index]) for index, plant in enumerate(CLASS_NAMES)},
                }
            )
    write_csv(args.output_dir / "known_failure_predictions.csv", prediction_rows)

    marigold_path = Path(next(row["path"] for row in known_rows if row["plant"] == "marigold"))
    gradcam_receipt: dict[str, Any] = {}
    figure_paths: dict[str, Path] = {}
    for model_name, model in models.items():
        probabilities = probability_cache[(model_name, "marigold")]
        rose_heatmap = gradcam(model, marigold_path, CLASS_NAMES.index("rose"))
        marigold_heatmap = gradcam(model, marigold_path, CLASS_NAMES.index("marigold"))
        np.save(args.output_dir / f"gradcam_{model_name}_rose.npy", rose_heatmap)
        np.save(args.output_dir / f"gradcam_{model_name}_marigold.npy", marigold_heatmap)
        figure_path = args.output_dir / f"gradcam_{model_name}_marigold_failure.png"
        figure_paths[model_name] = figure_path
        gradcam_figure(marigold_path, model_name, probabilities, rose_heatmap, marigold_heatmap, figure_path)
        gradcam_receipt[model_name] = {
            "target_rose": attention_metrics(marigold_path, rose_heatmap),
            "target_marigold": attention_metrics(marigold_path, marigold_heatmap),
            "last_convolution_layer": "efficientnetb0/top_conv",
        }
    gradcam_comparison(
        figure_paths["v5"], figure_paths["fresh_b0_run08"],
        args.output_dir / "gradcam_v5_vs_fresh_b0_marigold_failure.png",
    )
    write_json(args.output_dir / "gradcam_receipt.json", gradcam_receipt)

    train_rows = read_csv(args.train_manifest)
    sample_manifest: list[dict[str, Any]] = []
    for plant in ("marigold", "rose"):
        selected = deterministic_stratified_sample(train_rows, plant, 24, args.seed)
        for index, row in enumerate(selected, start=1):
            sample_manifest.append({"sample_index": index, "plant": plant, **row})
        contact_sheet(selected, args.output_dir / f"training_{plant}_contact_sheet.jpg", f"Run08 training — systematic {plant} sample (seed {args.seed})")
    write_csv(args.output_dir / "training_contact_sheet_manifest.csv", sample_manifest)

    debug_rows = read_csv(args.debug_predictions)
    error_rows = [
        row for row in debug_rows if row["correct"].lower() == "false" and row["true_plant"] in {"marigold", "chrysanthemum"}
    ]
    write_csv(args.output_dir / "internal_debug_target_errors.csv", error_rows)
    for plant in ("marigold", "chrysanthemum"):
        values = [row for row in error_rows if row["true_plant"] == plant]
        sheet_rows = [
            {
                **row,
                "caption": f"true={plant} pred={row['predicted_plant']} conf={float(row['top1_confidence']):.1%}\n{row['source']} | {Path(row['path']).name}",
            }
            for row in values
        ]
        contact_sheet(sheet_rows, args.output_dir / f"internal_debug_{plant}_errors.jpg", f"Fresh B0 Run08 internal-debug {plant} errors ({len(values)})")

    confusion_summary: dict[str, Any] = {}
    for plant in ("marigold", "chrysanthemum"):
        plant_rows = [row for row in debug_rows if row["true_plant"] == plant]
        errors = [row for row in plant_rows if row["correct"].lower() == "false"]
        confusion_summary[plant] = {
            "samples": len(plant_rows),
            "errors": len(errors),
            "predicted_labels_for_errors": dict(Counter(row["predicted_plant"] for row in errors)),
            "error_sources": dict(Counter(row["source"] for row in errors)),
        }

    distribution: dict[str, Any] = {}
    for plant in ("marigold", "rose"):
        plant_rows = [row for row in train_rows if row["plant"] == plant]
        stats = [(row, image_background_stats(Path(row["path"]))) for row in plant_rows]
        natural_count = sum(
            "inaturalist" in row.get("source", "").lower() or "natural" in row.get("source", "").lower()
            for row in plant_rows
        )
        distribution[plant] = {
            "samples": len(plant_rows),
            "source_counts": dict(Counter(row.get("source", "unknown") for row in plant_rows)),
            "natural_source_samples": natural_count,
            "natural_source_fraction": natural_count / len(plant_rows),
            "background_statistics": {
                key: summarise(value[key] for _, value in stats)
                for key in ("mean_brightness", "corner_brightness", "corner_std", "near_black_corner_fraction", "near_white_corner_fraction")
            },
        }

    report = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "purpose": "targeted_marigold_to_rose_error_analysis_no_training",
        "training_performed": False,
        "locked_or_legacy_test_used": False,
        "models": {
            "v5": {"path": str(args.v5_model), "sha256": sha256_file(args.v5_model)},
            "fresh_b0_run08": {"path": str(args.fresh_model), "sha256": sha256_file(args.fresh_model)},
        },
        "preprocessing_contract": {
            "decode": "tf.io.decode_image(channels=3, expand_animations=False)",
            "dtype": "float32",
            "resize": "tf.image.resize 224x224 bilinear antialias=False",
            "pixel_range": "0..255",
            "normalization": "EfficientNet embedded rescaling",
        },
        "known_failure_predictions": prediction_rows,
        "gradcam": gradcam_receipt,
        "training_distribution": distribution,
        "internal_debug_error_summary": confusion_summary,
        "interpretation_limits": [
            "Grad-CAM is a low-resolution association map and does not prove causal model reasoning.",
            "Known failures are diagnostic examples and were not used to claim production readiness.",
            "Internal Debug originates from the same audited source pool as training.",
        ],
    }
    write_json(args.output_dir / "analysis_report.json", report)
    print(json.dumps({
        "status": "completed",
        "output_dir": str(args.output_dir),
        "prediction_rows": len(prediction_rows),
        "debug_target_errors": len(error_rows),
        "training_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
