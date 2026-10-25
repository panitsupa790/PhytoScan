from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import sklearn
import tensorflow as tf
from matplotlib import pyplot as plt
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from preprocessing.eggplant import load_config as load_preprocessing_config
from preprocessing.eggplant import preprocess_image
from training.d7_mobilenetv2 import write_csv, write_json


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "ai_model/configs/eggplant_final_locked.json"
LOCK_MANIFEST_PATH = ROOT / "ai_model/experiments/eggplant_final/final_lock_manifest.json"
SPLIT_MANIFEST_PATH = ROOT / "dataset/metadata/eggplant_split_manifest.csv"
SPLIT_SUMMARY_PATH = ROOT / "dataset/metadata/eggplant_split_summary.json"
OUTPUT_ROOT = ROOT / "ai_model/experiments/eggplant_final/d11"
EXPECTED_CONFIG_SHA256 = "5a7663db4f8c648fe06ce4d62206f7267946d357cedc6af73a6a7c35f432899b"
EXPECTED_CHECKPOINT_SHA256 = "ae0be68277300848eb4208c5184bf9c937cbe2ea9c8d5abc363eb38976135aa5"
EXPECTED_ASSIGNMENT_SHA256 = "26861714087fffdffd5f098f3283bba5bebe9dbb6cc93bca30dbf4cf7d14d313"
EXPECTED_CLASSES = ("healthy", "leaf_spot", "mosaic_virus")
EXPECTED_TEST_COUNTS = {"healthy": 208, "leaf_spot": 74, "mosaic_virus": 203}


class D11Error(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assignment_digest(rows: Iterable[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            f"{row['class']}\0{row['filename']}\0{row['sha256']}\0{row['split']}\0{row['seed']}\n".encode(
                "utf-8"
            )
        )
    return digest.hexdigest()


def source_metadata_snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for relative_root in ("dataset/raw", "dataset/cleaned", "dataset/split"):
        source_root = ROOT / relative_root
        files = []
        paths = sorted(
            (item for item in source_root.rglob("*") if item.is_file()),
            key=lambda item: item.as_posix().casefold(),
        )
        for path in paths:
            stat = path.stat()
            files.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "size": stat.st_size,
                    "modified_time_ns": stat.st_mtime_ns,
                }
            )
        result[relative_root] = {
            "file_count": len(files),
            "total_bytes": sum(row["size"] for row in files),
            "files": files,
        }
    return result


def load_manifest() -> list[dict[str, str]]:
    with SPLIT_MANIFEST_PATH.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    required = {"class", "filename", "sha256", "split", "seed"}
    if not rows or set(rows[0]) != required:
        raise D11Error("Split manifest fields are not the locked D5 schema")
    return rows


def preflight(write_artifacts: bool = False) -> dict[str, Any]:
    config_hash = sha256_file(CONFIG_PATH)
    manifest = read_json(LOCK_MANIFEST_PATH)
    config = read_json(CONFIG_PATH)
    checkpoint_path = ROOT / config["source_checkpoint"]
    checkpoint_hash = sha256_file(checkpoint_path)
    rows = load_manifest()
    summary = read_json(SPLIT_SUMMARY_PATH)
    digest = assignment_digest(rows)

    split_counts = Counter(row["split"] for row in rows)
    class_split_counts = Counter((row["split"], row["class"]) for row in rows)
    identities = [(row["class"], row["filename"]) for row in rows]
    hash_splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        hash_splits[row["sha256"]].add(row["split"])
    leaked_hashes = [image_hash for image_hash, splits in hash_splits.items() if len(splits) > 1]
    test_rows = [row for row in rows if row["split"] == "test"]
    expected_test_paths = {
        (ROOT / "dataset/split/eggplant/test" / row["class"] / row["filename"]).resolve()
        for row in test_rows
    }
    actual_test_paths = {
        path.resolve()
        for class_name in EXPECTED_CLASSES
        for path in (ROOT / "dataset/split/eggplant/test" / class_name).iterdir()
        if path.is_file() and path.name != ".gitkeep"
    }
    checks = {
        "config_hash_matches_expected": config_hash == EXPECTED_CONFIG_SHA256 == manifest["final_config_sha256"],
        "checkpoint_hash_matches_expected": checkpoint_hash == EXPECTED_CHECKPOINT_SHA256 == manifest["checkpoint_sha256"] == config["checkpoint_sha256"],
        "lock_status": config["lock_status"] == "LOCKED_FOR_D11_FINAL_TEST",
        "source_run": config["source_run"] == "D9_R2",
        "class_mapping": tuple(config["class_names"]) == EXPECTED_CLASSES,
        "assignment_hash": digest == EXPECTED_ASSIGNMENT_SHA256 == summary["assignment_sha256"],
        "split_counts": dict(split_counts) == {"train": 2425, "val": 324, "test": 485},
        "test_class_counts": {name: class_split_counts[("test", name)] for name in EXPECTED_CLASSES} == EXPECTED_TEST_COUNTS,
        "unique_assignments": len(identities) == len(set(identities)) == 3234,
        "no_sha_overlap_across_splits": not leaked_hashes,
        "test_files_match_manifest": expected_test_paths == actual_test_paths,
        "test_evaluation_not_previously_recorded": not (OUTPUT_ROOT / "test_open_event.json").exists(),
    }
    result = {
        "pass": all(checks.values()),
        "checks": checks,
        "config_sha256": config_hash,
        "checkpoint_sha256": checkpoint_hash,
        "test_assignment_sha256": digest,
        "test_counts": {name: class_split_counts[("test", name)] for name in EXPECTED_CLASSES},
        "test_total": len(test_rows),
        "test_image_bytes_accessed": 0,
    }
    if write_artifacts:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        write_json(OUTPUT_ROOT / "preflight.json", result)
        write_json(OUTPUT_ROOT / "source_state_before.json", source_metadata_snapshot())
    if not result["pass"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise D11Error(f"D11 preflight failed before Test decode: {', '.join(failed)}")
    return result


def calculate_metrics(
    true_indices: np.ndarray, predicted_indices: np.ndarray, probabilities: np.ndarray
) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray]:
    labels = list(range(len(EXPECTED_CLASSES)))
    precision, recall, f1, support = precision_recall_fscore_support(
        true_indices, predicted_indices, labels=labels, zero_division=0
    )
    macro = precision_recall_fscore_support(
        true_indices, predicted_indices, labels=labels, average="macro", zero_division=0
    )
    weighted = precision_recall_fscore_support(
        true_indices, predicted_indices, labels=labels, average="weighted", zero_division=0
    )
    correct = true_indices == predicted_indices
    confidence = probabilities.max(axis=1)
    per_class = {
        name: {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
            "support": int(support[index]),
        }
        for index, name in enumerate(EXPECTED_CLASSES)
    }
    metrics = {
        "test_accuracy": float(accuracy_score(true_indices, predicted_indices)),
        "test_macro_precision": float(macro[0]),
        "test_macro_recall": float(macro[1]),
        "test_macro_f1": float(macro[2]),
        "test_weighted_precision": float(weighted[0]),
        "test_weighted_recall": float(weighted[1]),
        "test_weighted_f1": float(weighted[2]),
        "per_class": per_class,
        "zero_division": 0,
        "confidence": {
            "mean_overall": float(confidence.mean()),
            "mean_correct": float(confidence[correct].mean()) if correct.any() else None,
            "mean_incorrect": float(confidence[~correct].mean()) if (~correct).any() else None,
            "low_confidence_threshold": 0.6,
            "low_confidence_count": int((confidence < 0.6).sum()),
        },
    }
    report_rows = [
        {"class": name, **per_class[name]} for name in EXPECTED_CLASSES
    ]
    matrix = confusion_matrix(true_indices, predicted_indices, labels=labels)
    return metrics, report_rows, matrix


def plot_test_confusion(matrix: np.ndarray, output_path: Path, normalized: bool) -> None:
    values = matrix.astype(float)
    if normalized:
        row_sums = values.sum(axis=1, keepdims=True)
        values = np.divide(values, row_sums, out=np.zeros_like(values), where=row_sums != 0)
    figure, axis = plt.subplots(figsize=(6, 5))
    image = axis.imshow(values, cmap="Blues", vmin=0, vmax=1 if normalized else None)
    figure.colorbar(image, ax=axis)
    axis.set(
        xticks=range(len(EXPECTED_CLASSES)),
        yticks=range(len(EXPECTED_CLASSES)),
        xticklabels=EXPECTED_CLASSES,
        yticklabels=EXPECTED_CLASSES,
    )
    axis.set_xlabel("Predicted label")
    axis.set_ylabel("True label")
    axis.set_title("Final Test confusion matrix" + (" (row-normalized)" if normalized else ""))
    threshold = values.max() / 2 if values.size else 0
    for row in range(len(EXPECTED_CLASSES)):
        for column in range(len(EXPECTED_CLASSES)):
            label = f"{values[row, column]:.2f}" if normalized else str(int(values[row, column]))
            axis.text(
                column,
                row,
                label,
                ha="center",
                va="center",
                color="white" if values[row, column] > threshold else "black",
            )
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def evaluate_final_test() -> dict[str, Any]:
    preflight_result = preflight(write_artifacts=False)
    open_event_path = OUTPUT_ROOT / "test_open_event.json"
    if open_event_path.exists():
        raise D11Error("Test set was already opened for this locked model; refusing a second run")
    config = read_json(CONFIG_PATH)
    rows = [row for row in load_manifest() if row["split"] == "test"]
    class_to_index = {name: index for index, name in enumerate(config["class_names"])}
    rows.sort(key=lambda row: (class_to_index[row["class"]], row["filename"].casefold(), row["filename"]))
    open_event = {
        "event": "Test set opened for final evaluation",
        "opened_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": preflight_result["config_sha256"],
        "checkpoint_sha256": preflight_result["checkpoint_sha256"],
        "test_assignment_sha256": preflight_result["test_assignment_sha256"],
        "python_version": sys.version,
        "tensorflow_version": tf.__version__,
        "keras_version": tf.keras.__version__,
        "platform": platform.platform(),
        "devices": [str(device) for device in tf.config.list_physical_devices()],
        "status": "TEST_IS_NO_LONGER_UNSEEN_FOR_THIS_MODEL_VERSION",
    }
    write_json(open_event_path, open_event)

    checkpoint = ROOT / config["source_checkpoint"]
    model = tf.keras.models.load_model(checkpoint, compile=False)
    if list(model.input_shape[1:]) != config["input_size"] or model.output_shape[-1] != len(EXPECTED_CLASSES):
        raise D11Error("Locked model shape changed after Test-open event")
    preprocessing = load_preprocessing_config(ROOT / config["preprocessing"]["config_path"])
    batch_size = config["batch_size"]
    probability_batches = []
    test_bytes_accessed = 0
    started = time.perf_counter()
    for offset in range(0, len(rows), batch_size):
        batch_rows = rows[offset : offset + batch_size]
        images = []
        for row in batch_rows:
            path = ROOT / "dataset/split/eggplant/test" / row["class"] / row["filename"]
            image = preprocess_image(path, "P3", preprocessing)
            images.append(np.asarray(image, dtype=np.float32))
            test_bytes_accessed += 1
        batch = np.stack(images)
        probability_batches.append(np.asarray(model(batch, training=False), dtype=np.float64))
    duration_seconds = time.perf_counter() - started
    probabilities = np.concatenate(probability_batches, axis=0)
    true_indices = np.asarray([class_to_index[row["class"]] for row in rows], dtype=np.int32)
    predicted_indices = probabilities.argmax(axis=1).astype(np.int32)

    if probabilities.shape != (485, 3) or not np.isfinite(probabilities).all():
        raise D11Error("Final probability output is incomplete or non-finite")
    if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-5):
        raise D11Error("Final probability rows do not sum to one")
    metrics, report_rows, matrix = calculate_metrics(true_indices, predicted_indices, probabilities)
    if test_bytes_accessed != 485 or int(matrix.sum()) != 485:
        raise D11Error("Final Test evaluation did not cover exactly 485 images")

    prediction_rows = []
    for row, truth, prediction, probability in zip(rows, true_indices, predicted_indices, probabilities):
        prediction_rows.append(
            {
                "filename": row["filename"],
                "source_path": (Path("dataset/split/eggplant/test") / row["class"] / row["filename"]).as_posix(),
                "true_class": row["class"],
                "true_class_index": int(truth),
                "predicted_class": EXPECTED_CLASSES[int(prediction)],
                "predicted_class_index": int(prediction),
                "prob_healthy": float(probability[0]),
                "prob_leaf_spot": float(probability[1]),
                "prob_mosaic_virus": float(probability[2]),
                "correct": bool(truth == prediction),
            }
        )
    write_csv(
        OUTPUT_ROOT / "test_predictions.csv",
        [
            "filename", "source_path", "true_class", "true_class_index",
            "predicted_class", "predicted_class_index", "prob_healthy",
            "prob_leaf_spot", "prob_mosaic_virus", "correct",
        ],
        prediction_rows,
    )
    write_json(OUTPUT_ROOT / "test_metrics.json", metrics)
    write_csv(
        OUTPUT_ROOT / "classification_report.csv",
        ["class", "precision", "recall", "f1", "support"],
        report_rows,
    )
    matrix_rows = [
        {"actual": name, **{predicted: int(matrix[row, column]) for column, predicted in enumerate(EXPECTED_CLASSES)}}
        for row, name in enumerate(EXPECTED_CLASSES)
    ]
    write_csv(OUTPUT_ROOT / "confusion_matrix.csv", ["actual", *EXPECTED_CLASSES], matrix_rows)
    normalized = matrix.astype(float) / matrix.sum(axis=1, keepdims=True)
    normalized_rows = [
        {"actual": name, **{predicted: float(normalized[row, column]) for column, predicted in enumerate(EXPECTED_CLASSES)}}
        for row, name in enumerate(EXPECTED_CLASSES)
    ]
    write_csv(
        OUTPUT_ROOT / "confusion_matrix_normalized.csv",
        ["actual", *EXPECTED_CLASSES],
        normalized_rows,
    )
    plot_test_confusion(matrix, OUTPUT_ROOT / "confusion_matrix.png", False)
    plot_test_confusion(matrix, OUTPUT_ROOT / "confusion_matrix_normalized.png", True)
    validation = config["validation_evidence"]
    comparison = {
        "validation": validation,
        "final_test": {
            "accuracy": metrics["test_accuracy"],
            "macro_f1": metrics["test_macro_f1"],
            "leaf_spot_recall": metrics["per_class"]["leaf_spot"]["recall"],
            "leaf_spot_f1": metrics["per_class"]["leaf_spot"]["f1"],
        },
        "test_minus_validation_gap": {
            "accuracy": metrics["test_accuracy"] - validation["accuracy"],
            "macro_f1": metrics["test_macro_f1"] - validation["macro_f1"],
            "leaf_spot_recall": metrics["per_class"]["leaf_spot"]["recall"] - validation["leaf_spot_recall"],
            "leaf_spot_f1": metrics["per_class"]["leaf_spot"]["f1"] - validation["leaf_spot_f1"],
        },
        "used_for_tuning": False,
    }
    write_json(OUTPUT_ROOT / "validation_vs_test.json", comparison)
    metadata = {
        **open_event,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_duration_seconds": duration_seconds,
        "test_images_accessed": test_bytes_accessed,
        "unique_predictions": len({row["source_path"] for row in prediction_rows}),
        "training_performed": False,
        "fine_tuning_performed": False,
        "augmentation_used": False,
        "test_time_augmentation_used": False,
        "threshold_adjustment_used": False,
        "prediction_rule": "softmax_argmax",
        "checkpoint_selection_performed": False,
    }
    write_json(OUTPUT_ROOT / "evaluation_metadata.json", metadata)
    return {"metrics": metrics, "matrix": matrix.tolist(), "metadata": metadata}


def verify_source_unchanged() -> dict[str, Any]:
    before = read_json(OUTPUT_ROOT / "source_state_before.json")
    current = source_metadata_snapshot()
    unchanged = {name: before[name] == current[name] for name in before}
    result = {
        "method": "path, size, and modified-time metadata after the one-time Test evaluation",
        "unchanged": unchanged,
        "pass": all(unchanged.values()),
    }
    write_json(OUTPUT_ROOT / "source_state_verification.json", result)
    return result


def render_saved_confusion() -> dict[str, Any]:
    with (OUTPUT_ROOT / "confusion_matrix.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    matrix = np.asarray(
        [[int(row[name]) for name in EXPECTED_CLASSES] for row in rows], dtype=np.int64
    )
    if matrix.shape != (3, 3) or int(matrix.sum()) != 485:
        raise D11Error("Saved confusion matrix is invalid; refusing to render")
    plot_test_confusion(matrix, OUTPUT_ROOT / "confusion_matrix.png", False)
    plot_test_confusion(matrix, OUTPUT_ROOT / "confusion_matrix_normalized.png", True)
    return {"rendered_from_saved_matrix": True, "test_images_accessed": 0}
