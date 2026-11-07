from __future__ import annotations

import csv
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

from phyto_fasttrack.core import (
    CLASS_NAMES,
    ImageRecord,
    build_balanced_schedule,
    canonical_json_hash,
    overlap_summary,
)
from phyto_fasttrack.evaluation import prediction_metrics
from phyto_fasttrack.training import build_fresh_model


def record(index: int, label: str, source: str = "legacy") -> ImageRecord:
    return ImageRecord(
        path=Path(f"/tmp/{label}_{index}.jpg"),
        label=label,
        class_index=CLASS_NAMES.index(label),
        source=source,
        group_id=f"group_{label}_{index}",
        sha256=f"{index:064x}",
        row_number=index + 2,
    )


class BalancedScheduleTests(unittest.TestCase):
    def test_balances_classes_without_exceeding_repeat_cap(self) -> None:
        records = []
        sizes = [8, 3, 5, 7, 4, 6]
        for class_name, size in zip(CLASS_NAMES, sizes, strict=True):
            records.extend(record(index + CLASS_NAMES.index(class_name) * 100, class_name) for index in range(size))
        schedule, receipt = build_balanced_schedule(records, seed=42, max_repeats_per_image=2)
        counts = Counter(item.label for item in schedule)
        self.assertEqual(set(counts.values()), {6})
        repeats = Counter((str(item.path), item.row_number) for item in schedule)
        self.assertLessEqual(max(repeats.values()), 2)
        self.assertEqual(receipt["observed_max_repeats"], max(repeats.values()))

    def test_schedule_is_reproducible(self) -> None:
        records = [record(index, class_name, "natural" if index == 0 else "legacy") for class_name in CLASS_NAMES for index in range(4)]
        first, _ = build_balanced_schedule(records, seed=7, max_repeats_per_image=2)
        second, _ = build_balanced_schedule(records, seed=7, max_repeats_per_image=2)
        self.assertEqual([(item.path, item.row_number) for item in first], [(item.path, item.row_number) for item in second])


class EvaluationTests(unittest.TestCase):
    def test_metrics_respect_locked_class_order(self) -> None:
        labels = np.arange(len(CLASS_NAMES), dtype=np.int64)
        probabilities = np.eye(len(CLASS_NAMES), dtype=np.float32)
        metrics, predicted = prediction_metrics(labels, probabilities)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["macro_f1"], 1.0)
        self.assertEqual(predicted.tolist(), labels.tolist())

    def test_overlap_detects_path_sha_and_group(self) -> None:
        train = [record(1, CLASS_NAMES[0])]
        validation = [train[0]]
        overlap = overlap_summary(train, validation)
        self.assertEqual(overlap["path_count"], 1)
        self.assertEqual(overlap["sha256_count"], 1)
        self.assertEqual(overlap["group_count"], 1)

    def test_config_hash_ignores_dictionary_order(self) -> None:
        self.assertEqual(canonical_json_hash({"a": 1, "b": 2}), canonical_json_hash({"b": 2, "a": 1}))


class ModelBuilderTests(unittest.TestCase):
    def test_fresh_b0_contract_without_external_checkpoint(self) -> None:
        config = {
            "seed": 42,
            "augmentation": {
                "rotation_factor": 0.06,
                "zoom_factor": 0.08,
                "brightness_factor": 0.1,
                "contrast_factor": 0.12,
            },
            "model": {"dropout_rate": 0.3},
        }
        model, backbone = build_fresh_model(config, weights=None)
        self.assertEqual(model.input_shape, (None, 224, 224, 3))
        self.assertEqual(model.output_shape, (None, len(CLASS_NAMES)))
        self.assertFalse(backbone.trainable)
        self.assertEqual(model.get_layer("plant_probabilities").dtype_policy.name, "float32")


if __name__ == "__main__":
    unittest.main()
