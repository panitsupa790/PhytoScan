from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

import numpy as np


AI_MODEL_ROOT = Path(__file__).resolve().parents[1]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from evaluation.d11_final_test import (  # noqa: E402
    EXPECTED_ASSIGNMENT_SHA256,
    EXPECTED_CHECKPOINT_SHA256,
    EXPECTED_CONFIG_SHA256,
    OUTPUT_ROOT,
    calculate_metrics,
    read_json,
)


class D11EvaluationTests(unittest.TestCase):
    def test_preflight_passed_without_test_byte_access(self) -> None:
        result = read_json(OUTPUT_ROOT / "preflight.json")
        self.assertTrue(result["pass"])
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["config_sha256"], EXPECTED_CONFIG_SHA256)
        self.assertEqual(result["checkpoint_sha256"], EXPECTED_CHECKPOINT_SHA256)
        self.assertEqual(result["test_assignment_sha256"], EXPECTED_ASSIGNMENT_SHA256)
        self.assertEqual(result["test_image_bytes_accessed"], 0)

    def test_preflight_locked_test_counts(self) -> None:
        result = read_json(OUTPUT_ROOT / "preflight.json")
        self.assertEqual(result["test_counts"], {"healthy": 208, "leaf_spot": 74, "mosaic_virus": 203})
        self.assertEqual(result["test_total"], 485)

    def test_metric_calculation_uses_fixed_three_class_order(self) -> None:
        truth = np.asarray([0, 1, 2, 2], dtype=np.int32)
        probabilities = np.asarray(
            [[0.8, 0.1, 0.1], [0.2, 0.7, 0.1], [0.1, 0.6, 0.3], [0.1, 0.2, 0.7]],
            dtype=np.float64,
        )
        predictions = probabilities.argmax(axis=1)
        metrics, rows, matrix = calculate_metrics(truth, predictions, probabilities)
        self.assertAlmostEqual(metrics["test_accuracy"], 0.75)
        self.assertEqual([row["class"] for row in rows], ["healthy", "leaf_spot", "mosaic_virus"])
        self.assertEqual(int(matrix.sum()), 4)
        self.assertEqual(sum(row["support"] for row in rows), 4)
        self.assertEqual(metrics["zero_division"], 0)

    def test_final_predictions_are_complete_and_unique(self) -> None:
        with (OUTPUT_ROOT / "test_predictions.csv").open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 485)
        self.assertEqual(len({row["source_path"] for row in rows}), 485)
        self.assertEqual(
            {name: sum(row["true_class"] == name for row in rows) for name in ("healthy", "leaf_spot", "mosaic_virus")},
            {"healthy": 208, "leaf_spot": 74, "mosaic_virus": 203},
        )
        for row in rows:
            probabilities = np.asarray(
                [row["prob_healthy"], row["prob_leaf_spot"], row["prob_mosaic_virus"]],
                dtype=np.float64,
            )
            self.assertTrue(np.isfinite(probabilities).all())
            self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=5)
            self.assertEqual(int(probabilities.argmax()), int(row["predicted_class_index"]))

    def test_final_artifacts_record_no_training_or_tuning(self) -> None:
        metadata = read_json(OUTPUT_ROOT / "evaluation_metadata.json")
        self.assertEqual(metadata["test_images_accessed"], 485)
        self.assertFalse(metadata["training_performed"])
        self.assertFalse(metadata["fine_tuning_performed"])
        self.assertFalse(metadata["augmentation_used"])
        self.assertFalse(metadata["test_time_augmentation_used"])
        self.assertFalse(metadata["threshold_adjustment_used"])
        self.assertFalse(metadata["checkpoint_selection_performed"])
        self.assertEqual(metadata["status"], "TEST_IS_NO_LONGER_UNSEEN_FOR_THIS_MODEL_VERSION")

    def test_final_support_confusion_and_source_safety(self) -> None:
        metrics = read_json(OUTPUT_ROOT / "test_metrics.json")
        self.assertEqual(sum(row["support"] for row in metrics["per_class"].values()), 485)
        with (OUTPUT_ROOT / "confusion_matrix.csv").open(newline="", encoding="utf-8") as source:
            matrix_rows = list(csv.DictReader(source))
        matrix = np.asarray(
            [[int(row[name]) for name in ("healthy", "leaf_spot", "mosaic_virus")] for row in matrix_rows]
        )
        self.assertEqual(matrix.sum(), 485)
        np.testing.assert_array_equal(matrix.sum(axis=1), [208, 74, 203])
        self.assertTrue(read_json(OUTPUT_ROOT / "source_state_verification.json")["pass"])


if __name__ == "__main__":
    unittest.main()
