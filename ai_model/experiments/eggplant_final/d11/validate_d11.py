from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


AI_MODEL_ROOT = Path(__file__).resolve().parents[3]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from evaluation.d11_final_test import (  # noqa: E402
    CONFIG_PATH,
    EXPECTED_CHECKPOINT_SHA256,
    EXPECTED_CLASSES,
    EXPECTED_CONFIG_SHA256,
    EXPECTED_TEST_COUNTS,
    OUTPUT_ROOT,
    calculate_metrics,
    read_json,
    sha256_file,
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def main() -> int:
    config = read_json(CONFIG_PATH)
    checkpoint = AI_MODEL_ROOT.parent / config["source_checkpoint"]
    predictions = read_csv(OUTPUT_ROOT / "test_predictions.csv")
    metrics = read_json(OUTPUT_ROOT / "test_metrics.json")
    metadata = read_json(OUTPUT_ROOT / "evaluation_metadata.json")
    source_state = read_json(OUTPUT_ROOT / "source_state_verification.json")
    report = read_csv(OUTPUT_ROOT / "classification_report.csv")
    matrix_rows = read_csv(OUTPUT_ROOT / "confusion_matrix.csv")
    normalized_rows = read_csv(OUTPUT_ROOT / "confusion_matrix_normalized.csv")
    probabilities = np.asarray(
        [[float(row[f"prob_{name}"]) for name in EXPECTED_CLASSES] for row in predictions],
        dtype=np.float64,
    )
    truth = np.asarray([int(row["true_class_index"]) for row in predictions], dtype=np.int32)
    predicted = np.asarray([int(row["predicted_class_index"]) for row in predictions], dtype=np.int32)
    recomputed, _, matrix = calculate_metrics(truth, predicted, probabilities)
    class_counts = Counter(row["true_class"] for row in predictions)
    csv_matrix = np.asarray(
        [[int(row[name]) for name in EXPECTED_CLASSES] for row in matrix_rows], dtype=np.int64
    )
    normalized = np.asarray(
        [[float(row[name]) for name in EXPECTED_CLASSES] for row in normalized_rows], dtype=np.float64
    )
    required = (
        "test_predictions.csv", "test_metrics.json", "classification_report.csv",
        "confusion_matrix.csv", "confusion_matrix_normalized.csv", "confusion_matrix.png",
        "confusion_matrix_normalized.png", "evaluation_metadata.json", "test_open_event.json",
        "validation_vs_test.json", "source_state_verification.json", "D11_FINAL_TEST_REPORT.md",
    )
    checks = {
        "required_artifacts": all((OUTPUT_ROOT / name).is_file() for name in required),
        "config_hash": sha256_file(CONFIG_PATH) == EXPECTED_CONFIG_SHA256,
        "checkpoint_hash": sha256_file(checkpoint) == EXPECTED_CHECKPOINT_SHA256,
        "checkpoint_is_d9_r2": config["source_run"] == "D9_R2",
        "prediction_count": len(predictions) == 485,
        "unique_prediction_paths": len({row["source_path"] for row in predictions}) == 485,
        "test_class_counts": dict(class_counts) == EXPECTED_TEST_COUNTS,
        "probability_shape": probabilities.shape == (485, 3),
        "probabilities_finite": bool(np.isfinite(probabilities).all()),
        "probabilities_sum_to_one": bool(np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-5)),
        "argmax_mapping": bool(np.array_equal(probabilities.argmax(axis=1), predicted)),
        "class_name_mapping": all(row["predicted_class"] == EXPECTED_CLASSES[int(row["predicted_class_index"])] for row in predictions),
        "correct_flags": all((row["correct"] == "True") == (row["true_class_index"] == row["predicted_class_index"]) for row in predictions),
        "metrics_recomputed": all(abs(metrics[key] - recomputed[key]) < 1e-12 for key in ("test_accuracy", "test_macro_precision", "test_macro_recall", "test_macro_f1", "test_weighted_f1")),
        "classification_support": sum(int(row["support"]) for row in report) == 485,
        "confusion_total": int(csv_matrix.sum()) == 485,
        "confusion_rows": bool(np.array_equal(csv_matrix.sum(axis=1), [208, 74, 203])),
        "confusion_recomputed": bool(np.array_equal(csv_matrix, matrix)),
        "normalized_confusion": bool(np.allclose(normalized.sum(axis=1), 1.0)),
        "no_training": metadata["training_performed"] is False and metadata["fine_tuning_performed"] is False,
        "no_augmentation": metadata["augmentation_used"] is False and metadata["test_time_augmentation_used"] is False,
        "no_threshold_adjustment": metadata["threshold_adjustment_used"] is False and metadata["prediction_rule"] == "softmax_argmax",
        "no_checkpoint_selection": metadata["checkpoint_selection_performed"] is False,
        "test_open_recorded": metadata["test_images_accessed"] == 485 and metadata["status"] == "TEST_IS_NO_LONGER_UNSEEN_FOR_THIS_MODEL_VERSION",
        "source_data_unchanged": source_state["pass"],
    }
    result = {
        "pass": all(checks.values()),
        "passed": sum(checks.values()),
        "failed": sum(not value for value in checks.values()),
        "checks": checks,
    }
    (OUTPUT_ROOT / "validation_result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
