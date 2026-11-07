from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf
from PIL import Image


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.model_registry import get_classifier_config  # noqa: E402
from app.services.plant_classifier_service import PlantClassifierService  # noqa: E402
from scripts.evaluate_plant_classifier import (  # noqa: E402
    DEFAULT_VALIDATION,
    load_manifest,
    resolve_image_path,
    sha256_file,
)


DEFAULT_EXPORTED_LABELS = Path(
    r"C:\Users\HP\Desktop\PhytoScan\plant_classifier\labels.json"
)
DEFAULT_EXPORTED_MODEL = Path(
    r"C:\Users\HP\Desktop\PhytoScan\plant_classifier\plant-classifier-v1.keras"
)
REPORT_PATH = BACKEND_ROOT / "evaluation" / "plant_classifier_parity_audit.json"
REPORT_MARKDOWN_PATH = (
    BACKEND_ROOT / "evaluation" / "plant_classifier_parity_audit.md"
)


def ordered_rows_sha256(rows: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            ("\0".join(row[key] for key in ("path", "plant", "label", "split", "group_id")) + "\n").encode(
                "utf-8"
            )
        )
    return digest.hexdigest()


def notebook_prepare(path: Path, image_size: tuple[int, int]) -> np.ndarray:
    image_bytes = tf.io.read_file(str(path))
    image = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize(tf.cast(image, tf.float32), image_size)
    return np.asarray(image, dtype=np.float32)


def legacy_backend_prepare(path: Path, input_shape: tuple[int, int, int]) -> np.ndarray:
    content = path.read_bytes()
    with Image.open(BytesIO(content)) as decoded:
        decoded.load()
        rgb = decoded.convert("RGB")
    height, width, _channels = input_shape
    return np.asarray(
        rgb.resize((width, height), Image.Resampling.BILINEAR), dtype=np.float32
    )


def predict(model: Any, batch: list[np.ndarray]) -> np.ndarray:
    output = np.asarray(model(np.stack(batch), training=False), dtype=np.float32)
    if not np.isfinite(output).all() or not np.allclose(output.sum(axis=1), 1.0, atol=1e-5):
        raise ValueError("Invalid probability output")
    return output


def summarize(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    predictions = probabilities.argmax(axis=1)
    correct = predictions == labels
    return {
        "correct": int(correct.sum()),
        "incorrect": int((~correct).sum()),
        "total": int(len(labels)),
        "accuracy": float(correct.mean()),
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    config = get_classifier_config()
    rows = load_manifest(args.validation_manifest, "valid", config.class_order)
    exported_labels = json.loads(args.exported_labels.read_text(encoding="utf-8"))
    exported_class_order = tuple(exported_labels["class_names"])
    exported_mapping = {
        str(key): int(value) for key, value in exported_labels["class_to_idx"].items()
    }
    expected_mapping = {name: index for index, name in enumerate(config.class_order)}
    if exported_class_order != config.class_order or exported_mapping != expected_mapping:
        raise ValueError("Notebook export and runtime class mappings differ")
    runtime_hash = sha256_file(config.model_path)
    export_hash = sha256_file(args.exported_model)
    if runtime_hash != config.sha256 or export_hash != config.sha256:
        raise ValueError("Notebook export, manifest, and runtime model hashes differ")

    service = PlantClassifierService(config)
    labels = np.asarray([int(row["label"]) for row in rows], dtype=np.int64)
    notebook_outputs: list[np.ndarray] = []
    backend_outputs: list[np.ndarray] = []
    pixel_differences: list[float] = []
    for start in range(0, len(rows), args.batch_size):
        notebook_batch = []
        backend_batch = []
        for row in rows[start : start + args.batch_size]:
            path = resolve_image_path(row["path"])
            notebook_image = notebook_prepare(path, config.input_shape[:2])
            backend_image = legacy_backend_prepare(path, config.input_shape)
            notebook_batch.append(notebook_image)
            backend_batch.append(backend_image)
            pixel_differences.append(float(np.max(np.abs(notebook_image - backend_image))))
        notebook_outputs.append(predict(service.model, notebook_batch))
        backend_outputs.append(predict(service.model, backend_batch))
        print(f"audit {min(start + args.batch_size, len(rows))}/{len(rows)}", flush=True)

    notebook_probabilities = np.concatenate(notebook_outputs)
    backend_probabilities = np.concatenate(backend_outputs)
    notebook_predictions = notebook_probabilities.argmax(axis=1)
    backend_predictions = backend_probabilities.argmax(axis=1)
    disagreement_indexes = np.flatnonzero(notebook_predictions != backend_predictions)
    detail_indexes = np.unique(
        np.concatenate(
            (
                disagreement_indexes,
                np.flatnonzero(notebook_predictions != labels),
                np.flatnonzero(backend_predictions != labels),
            )
        )
    )
    details = []
    for index in detail_indexes:
        row = rows[int(index)]
        details.append(
            {
                "row_index": int(index),
                "path": row["path"],
                "true_label": int(labels[index]),
                "true_plant": config.class_order[int(labels[index])],
                "notebook_prediction": config.class_order[int(notebook_predictions[index])],
                "notebook_confidence": float(notebook_probabilities[index].max()),
                "backend_prediction": config.class_order[int(backend_predictions[index])],
                "backend_confidence": float(backend_probabilities[index].max()),
                "max_probability_delta": float(
                    np.max(np.abs(notebook_probabilities[index] - backend_probabilities[index]))
                ),
            }
        )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "validation_only_no_threshold_selection",
        "model": {
            "manifest_sha256": config.sha256,
            "runtime_sha256": runtime_hash,
            "notebook_export_sha256": export_hash,
            "all_equal": runtime_hash == export_hash == config.sha256,
        },
        "class_mapping": {
            "runtime_class_order": list(config.class_order),
            "notebook_export_class_order": list(exported_class_order),
            "all_equal": exported_class_order == config.class_order,
        },
        "validation_manifest": {
            "path": str(args.validation_manifest),
            "sha256": sha256_file(args.validation_manifest),
            "ordered_rows_sha256": ordered_rows_sha256(rows),
            "rows": len(rows),
            "labels_match_plant_column": all(
                config.class_order[int(row["label"])] == row["plant"] for row in rows
            ),
        },
        "preprocessing": {
            "notebook": "tf.io.decode_image(channels=3) -> tf.cast(float32) -> tf.image.resize(bilinear, 224x224)",
            "backend_before_fix": "Pillow decode -> convert(RGB) -> Pillow bilinear resize(224x224) -> float32",
            "images_with_nonzero_pixel_delta": int(sum(value != 0.0 for value in pixel_differences)),
            "maximum_absolute_pixel_delta": max(pixel_differences),
        },
        "results": {
            "notebook_compatible": summarize(labels, notebook_probabilities),
            "backend_before_fix": summarize(labels, backend_probabilities),
            "top1_prediction_disagreements": int(len(disagreement_indexes)),
            "maximum_absolute_probability_delta": float(
                np.max(np.abs(notebook_probabilities - backend_probabilities))
            ),
        },
        "affected_rows": details,
        "conclusion": "The model, class mapping, manifest row order, and labels match. The preprocessing implementation differs and changes top-1 predictions near decision boundaries.",
    }


def write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    results = report["results"]
    lines = [
        "# Plant Classifier Notebook/Backend Parity Audit",
        "",
        "Scope: Validation only. This audit does not select or modify thresholds and does not reopen Test.",
        "",
        f"- Model SHA-256 equal: `{report['model']['all_equal']}`",
        f"- Class mapping equal: `{report['class_mapping']['all_equal']}`",
        f"- Manifest labels match plant column: `{report['validation_manifest']['labels_match_plant_column']}`",
        f"- Notebook-compatible errors: `{results['notebook_compatible']['incorrect']}`",
        f"- Backend-before-fix errors: `{results['backend_before_fix']['incorrect']}`",
        f"- Top-1 disagreements: `{results['top1_prediction_disagreements']}`",
        "",
        "Conclusion: " + report["conclusion"],
    ]
    REPORT_MARKDOWN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-manifest", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--exported-labels", type=Path, default=DEFAULT_EXPORTED_LABELS)
    parser.add_argument("--exported-model", type=Path, default=DEFAULT_EXPORTED_MODEL)
    parser.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = audit(args)
    write_report(report)
    print(json.dumps(report["results"], indent=2))


if __name__ == "__main__":
    main()
