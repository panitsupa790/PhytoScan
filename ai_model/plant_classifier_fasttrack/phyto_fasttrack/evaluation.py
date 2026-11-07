from __future__ import annotations

import platform
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, recall_score

from .core import (
    CLASS_NAMES,
    FastTrackError,
    ImageRecord,
    class_counts,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
)


def make_inference_dataset(records: Sequence[ImageRecord], batch_size: int):
    import tensorflow as tf

    if not records:
        raise FastTrackError("Evaluation dataset is empty")
    paths = [str(record.path) for record in records]
    labels = [record.class_index for record in records]

    def decode(path: "tf.Tensor", label: "tf.Tensor"):
        data = tf.io.read_file(path)
        image = tf.io.decode_image(data, channels=3, expand_animations=False)
        image.set_shape([None, None, 3])
        image = tf.cast(image, tf.float32)
        image = tf.image.resize(image, [224, 224], method="bilinear", antialias=False)
        return image, label

    options = tf.data.Options()
    options.experimental_deterministic = True
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels)).with_options(options)
    return dataset.map(decode, num_parallel_calls=tf.data.AUTOTUNE).batch(batch_size).prefetch(2)


def _validate_model_contract(model: Any) -> None:
    input_shape = model.input_shape
    output_shape = model.output_shape
    if isinstance(input_shape, list) or isinstance(output_shape, list):
        raise FastTrackError("Only a single-input, single-output classifier is supported")
    if tuple(input_shape[-3:]) != (224, 224, 3):
        raise FastTrackError(f"Model input contract mismatch: {input_shape}")
    if int(output_shape[-1]) != len(CLASS_NAMES):
        raise FastTrackError(f"Model output has {output_shape[-1]} classes, expected {len(CLASS_NAMES)}")


def prediction_metrics(labels: np.ndarray, probabilities: np.ndarray) -> tuple[dict[str, Any], np.ndarray]:
    if probabilities.shape != (len(labels), len(CLASS_NAMES)):
        raise FastTrackError(f"Unexpected prediction shape {probabilities.shape}")
    if not np.isfinite(probabilities).all():
        raise FastTrackError("Predictions contain NaN or Inf")
    predictions = probabilities.argmax(axis=1)
    matrix = confusion_matrix(labels, predictions, labels=np.arange(len(CLASS_NAMES)))
    per_class_recall = recall_score(
        labels, predictions, labels=np.arange(len(CLASS_NAMES)), average=None, zero_division=0
    )
    report = classification_report(
        labels,
        predictions,
        labels=np.arange(len(CLASS_NAMES)),
        target_names=CLASS_NAMES,
        output_dict=True,
        zero_division=0,
    )
    metrics = {
        "samples": int(len(labels)),
        "correct": int((predictions == labels).sum()),
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(f1_score(labels, predictions, labels=np.arange(len(CLASS_NAMES)), average="macro", zero_division=0)),
        "macro_recall": float(recall_score(labels, predictions, labels=np.arange(len(CLASS_NAMES)), average="macro", zero_division=0)),
        "per_class_recall": {name: float(per_class_recall[index]) for index, name in enumerate(CLASS_NAMES)},
        "classification_report": report,
        "confusion_matrix": matrix.astype(int).tolist(),
    }
    return metrics, predictions


def evaluate_model(
    *,
    model_path: Path,
    records: Sequence[ImageRecord],
    manifest_path: Path,
    output_dir: Path,
    dataset_role: str,
    batch_size: int,
    notes: Sequence[str] = (),
) -> dict[str, Any]:
    import tensorflow as tf

    if output_dir.exists():
        raise FastTrackError(f"Refusing to overwrite evaluation directory: {output_dir}")
    output_dir.mkdir(parents=True)
    started = time.perf_counter()
    model = tf.keras.models.load_model(model_path, compile=False)
    _validate_model_contract(model)
    dataset = make_inference_dataset(records, batch_size)
    probabilities = np.asarray(model.predict(dataset.map(lambda image, label: image), verbose=1), dtype=np.float32)
    labels = np.asarray([record.class_index for record in records], dtype=np.int64)
    metrics, predictions = prediction_metrics(labels, probabilities)
    duration = time.perf_counter() - started

    rows: list[dict[str, Any]] = []
    for record, predicted_index, scores in zip(records, predictions, probabilities, strict=True):
        ordered = np.argsort(scores)[::-1]
        top1 = int(ordered[0])
        top2 = int(ordered[1])
        row: dict[str, Any] = {
            "manifest_row": record.row_number,
            "path": str(record.path),
            "true_plant": record.label,
            "predicted_plant": CLASS_NAMES[int(predicted_index)],
            "correct": bool(int(predicted_index) == record.class_index),
            "top1_confidence": float(scores[top1]),
            "top2_plant": CLASS_NAMES[top2],
            "top2_confidence": float(scores[top2]),
            "top1_top2_margin": float(scores[top1] - scores[top2]),
            "source": record.source,
            "group_id": record.group_id or "",
        }
        row.update({f"p_{name}": float(scores[index]) for index, name in enumerate(CLASS_NAMES)})
        rows.append(row)
    prediction_columns = [
        "manifest_row",
        "path",
        "true_plant",
        "predicted_plant",
        "correct",
        "top1_confidence",
        "top2_plant",
        "top2_confidence",
        "top1_top2_margin",
        "source",
        "group_id",
        *[f"p_{name}" for name in CLASS_NAMES],
    ]
    write_csv(output_dir / "row_predictions.csv", prediction_columns, rows)
    matrix_rows = [
        {"true_plant": name, **{predicted: int(metrics["confusion_matrix"][row][column]) for column, predicted in enumerate(CLASS_NAMES)}}
        for row, name in enumerate(CLASS_NAMES)
    ]
    write_csv(output_dir / "confusion_matrix.csv", ["true_plant", *CLASS_NAMES], matrix_rows)
    receipt = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "dataset_role": dataset_role,
        "notes": list(notes),
        "metrics": metrics,
        "class_counts": class_counts(records),
        "class_order": list(CLASS_NAMES),
        "preprocessing_contract": {
            "decode": "tf.io.decode_image(channels=3, expand_animations=False)",
            "dtype": "float32",
            "resize": "tf.image.resize(224x224, bilinear, antialias=False)",
            "pixel_range": "0-255",
            "normalization": "EfficientNet embedded rescaling",
        },
        "model": {"path": str(model_path), "sha256": sha256_file(model_path)},
        "manifest": {"path": str(manifest_path), "sha256": sha256_file(manifest_path)},
        "runtime": {
            "duration_seconds": duration,
            "images_per_second": len(records) / duration if duration else None,
            "tensorflow": tf.__version__,
            "keras": getattr(tf.keras, "__version__", "unknown"),
            "python": sys.version,
            "platform": platform.platform(),
        },
    }
    write_json(output_dir / "evaluation.json", receipt)
    return receipt
