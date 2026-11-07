from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import app.services.model_registry as model_registry
import app.services.threshold_config as threshold_config
from app.services.model_input import prepare_model_input


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
CANDIDATE_MANIFEST = APP_ROOT / "data" / "model_manifest.hybrid_candidate.json"
CANDIDATE_THRESHOLD = (
    APP_ROOT / "data" / "plant_classifier_threshold.hybrid_candidate.json"
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (13, 17), color=(22, 101, 45)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_candidate_bundle_is_hybrid_and_not_active() -> None:
    candidate = read_json(CANDIDATE_MANIFEST)
    active = read_json(APP_ROOT / "data" / "model_manifest.json")
    assert candidate["status"] == "candidate_staging_not_active"
    assert candidate["activation_requires_explicit_approval"] is True
    assert active["plant_classifier"]["sha256"] != candidate["plant_classifier"]["sha256"]
    assert candidate["plant_classifier"]["architecture"] == "MobileNetV2"
    architectures = {
        plant: model["architecture"] for plant, model in candidate["models"].items()
    }
    assert architectures == {
        "chrysanthemum": "MobileNetV2",
        "marigold": "EfficientNetB0",
        "money_plant": "MobileNetV2",
        "rose": "MobileNetV2",
        "snake_plant": "MobileNetV2",
        "spider_plant": "MobileNetV2",
    }
    assert "sunflower" not in candidate["models"]


def test_candidate_model_files_match_manifest_sha256() -> None:
    candidate = read_json(CANDIDATE_MANIFEST)
    entries = [candidate["plant_classifier"], *candidate["models"].values()]
    for entry in entries:
        path = APP_ROOT / entry["model_path"]
        assert path.is_file()
        assert sha256_file(path) == entry["sha256"]


def test_mobile_and_efficient_contracts_preserve_raw_rgb_0_255() -> None:
    payload = image_bytes()
    kwargs = {
        "content": payload,
        "input_shape": (224, 224, 3),
        "decoder": "tensorflow_decode_image_rgb",
        "resize_method": "tensorflow_bilinear",
    }
    mobile = prepare_model_input(
        preprocessing="mobilenet_v2_embedded_minus1_1_from_0_255", **kwargs
    )
    efficient = prepare_model_input(
        preprocessing="efficientnet_embedded_rescaling_from_0_255", **kwargs
    )
    np.testing.assert_array_equal(mobile, efficient)
    assert mobile.dtype == np.float32
    assert float(mobile.min()) >= 0.0
    assert float(mobile.max()) <= 255.0


def test_candidate_registry_mapping_and_frozen_threshold(monkeypatch) -> None:
    monkeypatch.setattr(model_registry, "_manifest_path", lambda: CANDIDATE_MANIFEST)
    model_registry.get_classifier_config.cache_clear()
    model_registry.get_registry.cache_clear()
    try:
        classifier = model_registry.get_classifier_config()
        registry = model_registry.get_registry()
        assert classifier.sha256 == "fa53ab449421b12c9b3244d380ecd68633514d5752d1b4167772b0453abdfad4"
        assert registry["marigold"].architecture == "EfficientNetB0"
        assert all(
            config.architecture == "MobileNetV2"
            for code, config in registry.items()
            if code != "marigold"
        )

        monkeypatch.setattr(threshold_config, "CONFIG_PATH", CANDIDATE_THRESHOLD)
        monkeypatch.setattr(threshold_config, "REQUIRE_TEST_RECEIPT", False)
        monkeypatch.setattr(
            threshold_config, "get_classifier_config", lambda: classifier
        )
        threshold_config.get_plant_thresholds.cache_clear()
        thresholds = threshold_config.get_plant_thresholds()
        assert thresholds.min_confidence == 0.0
        assert thresholds.min_margin == 0.34551629424095154
    finally:
        threshold_config.get_plant_thresholds.cache_clear()
        model_registry.get_classifier_config.cache_clear()
        model_registry.get_registry.cache_clear()


def test_candidate_production_mode_fails_closed_without_test_receipt(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(model_registry, "_manifest_path", lambda: CANDIDATE_MANIFEST)
    model_registry.get_classifier_config.cache_clear()
    try:
        classifier = model_registry.get_classifier_config()
        monkeypatch.setattr(threshold_config, "CONFIG_PATH", CANDIDATE_THRESHOLD)
        monkeypatch.setattr(
            threshold_config, "RECEIPT_PATH", tmp_path / "missing-receipt.json"
        )
        monkeypatch.setattr(threshold_config, "REQUIRE_TEST_RECEIPT", True)
        monkeypatch.setattr(
            threshold_config, "get_classifier_config", lambda: classifier
        )
        threshold_config.get_plant_thresholds.cache_clear()
        with pytest.raises(ValueError, match="unavailable"):
            threshold_config.get_plant_thresholds()
    finally:
        threshold_config.get_plant_thresholds.cache_clear()
        model_registry.get_classifier_config.cache_clear()
