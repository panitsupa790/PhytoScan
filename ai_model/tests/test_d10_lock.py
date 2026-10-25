from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[1]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from finalization.d10_lock import (
    CHECKPOINT_PATH,
    EXPERIMENT_ROOT,
    FINAL_CONFIG_PATH,
    PREPROCESSING_CONFIG_PATH,
    read_json,
    sha256_file,
    verify_model,
)


class D10LockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = read_json(FINAL_CONFIG_PATH)
        cls.manifest = read_json(EXPERIMENT_ROOT / "final_lock_manifest.json")

    def test_required_identity_fields_are_locked(self) -> None:
        self.assertEqual(self.config["lock_status"], "LOCKED_FOR_D11_FINAL_TEST")
        self.assertEqual(self.config["source_run"], "D9_R2")
        self.assertEqual(self.config["model"], "EfficientNetB0")
        self.assertEqual(self.config["input_size"], [224, 224, 3])
        self.assertEqual(self.config["pretrained_weights"], "imagenet")

    def test_class_mapping_matches_d9_r2(self) -> None:
        d9 = read_json(CHECKPOINT_PATH.parent / "config_snapshot.json")
        self.assertEqual(self.config["class_names"], d9["classes"])
        self.assertEqual(
            self.config["class_mapping"],
            {str(index): name for index, name in enumerate(d9["classes"])},
        )

    def test_config_and_checkpoint_hashes_are_reproducible(self) -> None:
        self.assertEqual(sha256_file(FINAL_CONFIG_PATH), self.manifest["final_config_sha256"])
        self.assertEqual(sha256_file(CHECKPOINT_PATH), self.manifest["checkpoint_sha256"])
        self.assertEqual(self.config["checkpoint_sha256"], self.manifest["checkpoint_sha256"])

    def test_p3_preprocessing_matches_source_config(self) -> None:
        source = read_json(PREPROCESSING_CONFIG_PATH)
        locked = self.config["preprocessing"]
        self.assertEqual(self.config["preprocessing_variant"], "P3")
        self.assertEqual(locked["resize_policy"], source["resize"]["policy"])
        self.assertEqual(locked["interpolation"], source["resize"]["interpolation"])
        self.assertEqual(locked["pad_color_rgb"], source["resize"]["pad_color_rgb"])
        self.assertEqual(locked["method"], source["variants"]["P3"]["method"])
        self.assertEqual(locked["parameters"], source["variants"]["P3"]["parameters"])

    def test_class_weights_match_d9_r2(self) -> None:
        d9 = read_json(CHECKPOINT_PATH.parent / "class_weights.json")
        self.assertTrue(d9["enabled"])
        self.assertEqual(self.config["class_weights"], d9["weights_by_class"])
        self.assertEqual(self.config["class_weight_formula"], d9["formula"])

    def test_fine_tuning_and_augmentation_are_locked(self) -> None:
        policy = read_json(CHECKPOINT_PATH.parent / "fine_tune_policy.json")
        self.assertEqual(self.config["fine_tuned_top_layers"], 20)
        self.assertEqual(self.config["fine_tuned_layer_names"], policy["window_layer_names"])
        self.assertTrue(self.config["batchnorm_frozen"])
        self.assertEqual(self.config["learning_rate"], 1e-5)
        self.assertEqual(self.config["batch_size"], 32)
        self.assertFalse(self.config["augmentation"])

    def test_checkpoint_loads_with_three_class_output(self) -> None:
        model = verify_model()
        self.assertTrue(model["load_successful"])
        self.assertEqual(model["output_classes"], 3)
        self.assertEqual(model["input_shape"], [224, 224, 3])
        self.assertEqual(model["batch_normalization_trainable"], 0)

    def test_d10_keeps_test_frozen(self) -> None:
        audit = read_json(EXPERIMENT_ROOT / "d10_access_audit.json")
        self.assertEqual(self.config["dataset_counts"], {"train": 2425, "val": 324, "test": 485})
        self.assertEqual(self.config["test_class_counts"], {"healthy": 208, "leaf_spot": 74, "mosaic_virus": 203})
        self.assertFalse(self.config["test_evaluated"])
        self.assertEqual(audit["test_image_bytes_accessed"], 0)
        self.assertEqual(audit["test_images_decoded"], 0)
        self.assertFalse(audit["test_inference_performed"])


if __name__ == "__main__":
    unittest.main()
