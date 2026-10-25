from __future__ import annotations

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
from training.d7_mobilenetv2 import (  # noqa: E402
    AccessAudit,
    D7Error,
    ImageRecord,
    build_model,
    load_records,
    load_training_config,
    make_dataset,
    parameter_counts,
)


class D7PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_training_config()
        cls.preprocessing_config = load_preprocessing_config()

    def test_locked_configuration(self) -> None:
        self.assertFalse(self.config["preprocessing"]["augmentation_enabled"])
        self.assertFalse(self.config["preprocessing"]["class_balancing_enabled"])
        self.assertFalse(self.config["model"]["backbone_trainable"])
        self.assertEqual(self.config["data"]["expected_counts"]["test"], 0)

    def test_manifest_counts_and_test_request_rejected(self) -> None:
        self.assertEqual(len(load_records(self.config, ["train"])), 2425)
        self.assertEqual(len(load_records(self.config, ["val"])), 324)
        with self.assertRaises(D7Error):
            load_records(self.config, ["test"])

    def test_access_audit_rejects_test_before_io(self) -> None:
        root = Path(__file__).resolve().parents[2] / "dataset" / "split" / "eggplant"
        audit = AccessAudit(root.resolve())
        with self.assertRaises(D7Error):
            audit.record(root / "test" / "healthy" / "never-opened.jpg", "test")
        self.assertEqual(audit.summary()["test_image_bytes_accessed"], 0)

    def test_dataset_uses_d6_then_single_mobilenet_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            split_root = Path(temp_dir) / "eggplant"
            source = split_root / "train" / "healthy" / "red.png"
            source.parent.mkdir(parents=True)
            Image.new("RGB", (224, 224), (255, 0, 0)).save(source)
            record = ImageRecord("train", "healthy", 0, source.name, source)
            audit = AccessAudit(split_root.resolve())
            dataset = make_dataset([record], "P0", self.config, self.preprocessing_config, audit, training=False)
            images, labels = next(iter(dataset))
            self.assertEqual(tuple(images.shape), (1, 224, 224, 3))
            center = images.numpy()[0, 112, 112]
            np.testing.assert_allclose(center, [1.0, -1.0, -1.0], atol=1e-6)
            self.assertEqual(int(labels.numpy()[0]), 0)

    def test_model_architecture_and_frozen_backbone(self) -> None:
        model = build_model(self.config, weights=None)
        self.assertEqual(model.input_shape, (None, 224, 224, 3))
        self.assertEqual(model.output_shape, (None, 3))
        counts = parameter_counts(model)
        self.assertGreater(counts["non_trainable"], counts["trainable"])
        self.assertEqual(model.get_layer("mobilenetv2_1.00_224").trainable, False)
        self.assertEqual(model.get_layer("disease_probabilities").activation, tf.keras.activations.softmax)


if __name__ == "__main__":
    unittest.main()
