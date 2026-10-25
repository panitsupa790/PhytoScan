from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image


AI_MODEL_ROOT = Path(__file__).resolve().parents[1]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from preprocessing.eggplant import load_config as load_preprocessing_config  # noqa: E402
from training.d7_mobilenetv2 import AccessAudit, ImageRecord, evaluate_predictions  # noqa: E402
from training.d9_refinement import (  # noqa: E402
    D9Error,
    build_augmentation,
    calculate_class_weights,
    load_and_configure_model,
    load_training_config,
    make_dataset,
    sha256_file,
)


class D9PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_training_config()
        cls.preprocessing_config = load_preprocessing_config()

    def test_r0_checkpoint_and_class_mapping(self) -> None:
        root = Path(__file__).resolve().parents[2]
        checkpoint = root / self.config["source"]["checkpoint"]
        self.assertEqual(sha256_file(checkpoint), self.config["source"]["checkpoint_sha256"])
        self.assertEqual(self.config["classes"], ["healthy", "leaf_spot", "mosaic_virus"])

    def test_fine_tune_window_and_batch_norm_policy(self) -> None:
        model, policy = load_and_configure_model(self.config)
        self.assertEqual(model.output_shape, (None, 3))
        self.assertEqual(policy["top_layer_window"], 20)
        self.assertEqual(policy["window_first_index"], 218)
        self.assertEqual(policy["batch_normalization_trainable"], 0)
        self.assertEqual(policy["trainable_weight_layers"], [
            "block6d_project_conv", "block7a_expand_conv", "block7a_dwconv",
            "block7a_se_reduce", "block7a_se_expand", "block7a_project_conv", "top_conv",
        ])

    def test_balanced_class_weights_use_locked_train_counts(self) -> None:
        weights = calculate_class_weights(self.config)
        self.assertAlmostEqual(weights[0], 2425 / (3 * 1039))
        self.assertAlmostEqual(weights[1], 2425 / (3 * 371))
        self.assertAlmostEqual(weights[2], 2425 / (3 * 1015))

    def test_augmentation_layers_are_conservative(self) -> None:
        augmentation = build_augmentation(self.config)
        self.assertEqual([layer.__class__.__name__ for layer in augmentation.layers], [
            "RandomFlip", "RandomRotation", "RandomZoom", "RandomTranslation"
        ])

    def test_validation_augmentation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            split_root = Path(temp_dir) / "eggplant"
            source = split_root / "val" / "healthy" / "image.png"
            source.parent.mkdir(parents=True)
            Image.new("RGB", (224, 224), (0, 255, 0)).save(source)
            record = ImageRecord("val", "healthy", 0, source.name, source)
            audit = AccessAudit(split_root)
            with self.assertRaises(D9Error):
                make_dataset([record], self.config, self.preprocessing_config, audit, False, True)

    def test_metric_calculation(self) -> None:
        labels = np.array([0, 1, 2])
        predictions = np.eye(3, dtype=np.float32)
        metrics, _, matrix = evaluate_predictions(labels, predictions, self.config["classes"])
        self.assertEqual(metrics["validation_macro_f1"], 1.0)
        np.testing.assert_array_equal(matrix, np.eye(3, dtype=int))


if __name__ == "__main__":
    unittest.main()
