from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


AI_MODEL_ROOT = Path(__file__).resolve().parents[1]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from preprocessing.eggplant import (  # noqa: E402
    VARIANTS,
    PreprocessingError,
    load_config,
    preprocess_image,
)


class PreprocessingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()
        self.source = Image.new("RGB", (320, 180), (255, 0, 0))

    def test_config_loads_expected_variants_and_safety_flags(self) -> None:
        self.assertEqual(set(self.config["variants"]), set(VARIANTS))
        self.assertFalse(self.config["augmentation"]["enabled"])
        self.assertFalse(self.config["class_balancing"]["enabled"])
        self.assertFalse(self.config["output"]["model_specific_normalization"])

    def test_every_variant_returns_224_rgb_uint8_pixels(self) -> None:
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                output = preprocess_image(self.source, variant, self.config)
                self.assertEqual(output.size, (224, 224))
                self.assertEqual(output.mode, "RGB")
                self.assertEqual(len(output.getbands()), 3)
                minimum, maximum = output.getextrema()[0]
                self.assertGreaterEqual(minimum, 0)
                self.assertLessEqual(maximum, 255)

    def test_every_variant_is_deterministic(self) -> None:
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                first = preprocess_image(self.source, variant, self.config).tobytes()
                second = preprocess_image(self.source, variant, self.config).tobytes()
                self.assertEqual(hashlib.sha256(first).digest(), hashlib.sha256(second).digest())

    def test_pil_source_is_not_modified(self) -> None:
        before = self.source.tobytes()
        before_size = self.source.size
        preprocess_image(self.source, "P3", self.config)
        self.assertEqual(self.source.tobytes(), before)
        self.assertEqual(self.source.size, before_size)

    def test_path_source_is_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.png"
            self.source.save(source_path)
            before = source_path.read_bytes()
            preprocess_image(source_path, "P1", self.config)
            self.assertEqual(source_path.read_bytes(), before)

    def test_invalid_variant_is_rejected(self) -> None:
        with self.assertRaises(PreprocessingError):
            preprocess_image(self.source, "P9", self.config)

    def test_rgb_red_is_not_treated_as_bgr_blue(self) -> None:
        output = preprocess_image(self.source, "P0", self.config)
        red, green, blue = output.getpixel((112, 112))
        self.assertGreater(red, 250)
        self.assertLess(green, 5)
        self.assertLess(blue, 5)


if __name__ == "__main__":
    unittest.main()
