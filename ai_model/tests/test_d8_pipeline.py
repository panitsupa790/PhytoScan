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
from training.d7_mobilenetv2 import AccessAudit, ImageRecord, load_records  # noqa: E402
from training.d8_efficientnetb0 import (  # noqa: E402
    D8Error,
    build_frozen_feature_models,
    load_training_config,
    make_dataset,
)


class D8PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_training_config()
        cls.preprocessing_config = load_preprocessing_config()

    def test_locked_configuration_and_counts(self) -> None:
        self.assertEqual(self.config["preprocessing"]["variants"], ["P0", "P3"])
        self.assertFalse(self.config["preprocessing"]["augmentation_enabled"])
        self.assertFalse(self.config["preprocessing"]["class_balancing_enabled"])
        self.assertFalse(self.config["model"]["backbone_trainable"])
        self.assertEqual(len(load_records(self.config, ["train"])), 2425)
        self.assertEqual(len(load_records(self.config, ["val"])), 324)

    def test_invalid_variant_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit = AccessAudit(Path(temp_dir))
            with self.assertRaises(D8Error):
                make_dataset([], "P2", self.config, self.preprocessing_config, audit)

    def test_input_remains_0_255_for_internal_model_rescaling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            split_root = Path(temp_dir) / "eggplant"
            source = split_root / "train" / "healthy" / "white.png"
            source.parent.mkdir(parents=True)
            Image.new("RGB", (224, 224), (255, 255, 255)).save(source)
            record = ImageRecord("train", "healthy", 0, source.name, source)
            audit = AccessAudit(split_root.resolve())
            images, _ = next(iter(make_dataset([record], "P0", self.config, self.preprocessing_config, audit)))
            self.assertEqual(images.dtype, tf.float32)
            np.testing.assert_allclose(images.numpy()[0, 112, 112], [255.0, 255.0, 255.0])

    def test_efficientnet_has_internal_rescaling_and_frozen_backbone(self) -> None:
        extractor, _, full_model = build_frozen_feature_models(self.config, weights=None)
        backbone = extractor.get_layer("efficientnetb0")
        self.assertFalse(backbone.trainable)
        rescaling = backbone.get_layer("rescaling")
        self.assertAlmostEqual(float(rescaling.scale), 1.0 / 255.0)
        self.assertEqual(full_model.input_shape, (None, 224, 224, 3))
        self.assertEqual(full_model.output_shape, (None, 3))


if __name__ == "__main__":
    unittest.main()
