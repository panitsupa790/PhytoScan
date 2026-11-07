from __future__ import annotations

import hashlib
import json
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_final_metadata_matches_active_runtime_artifacts() -> None:
    metadata = read_json(APP_ROOT / "data" / "plant_classifier_final_metadata.json")
    manifest = read_json(APP_ROOT / "data" / "model_manifest.json")
    thresholds = read_json(
        APP_ROOT / "data" / "plant_classifier_evaluation_corrective.json"
    )

    selected = metadata["selected_model"]
    active = manifest["plant_classifier"]
    assert metadata["status"] == "final_integration_baseline"
    assert selected["model_version"] == active["model_version"]
    assert selected["class_order"] == active["class_order"]
    assert selected["input_shape"] == active["input_shape"]
    assert selected["sha256"] == active["sha256"]
    assert selected["sha256"] == thresholds["model"]["sha256"]

    model_path = APP_ROOT / active["model_path"]
    assert sha256_file(model_path) == selected["sha256"]
    assert metadata["runtime_thresholds"]["min_confidence"] == thresholds[
        "thresholds"
    ]["min_confidence"]
    assert metadata["runtime_thresholds"]["min_margin"] == thresholds["thresholds"][
        "min_margin"
    ]


def test_final_metadata_explicitly_limits_claims_to_controlled_backgrounds() -> None:
    metadata = read_json(APP_ROOT / "data" / "plant_classifier_final_metadata.json")
    unsupported = metadata["scope"]["not_supported_claims"]
    assert "general natural-scene plant recognition" in unsupported
    assert "unsupported/OOD plant detection" in unsupported
    assert metadata["selection"]["claim"] == (
        "final integration baseline; not proven globally most accurate"
    )
