from __future__ import annotations

import json
import hashlib
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.model_registry import get_classifier_config


APP_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = APP_ROOT.parent
def _configured_backend_path(raw_path: str) -> Path:
    configured = Path(raw_path)
    if configured.is_absolute():
        return configured.resolve()
    return (BACKEND_ROOT / configured).resolve()


CONFIG_PATH = _configured_backend_path(settings.plant_threshold_config)
RECEIPT_PATH = _configured_backend_path(settings.plant_threshold_receipt)
REQUIRE_TEST_RECEIPT = settings.plant_threshold_require_test_receipt
TEST_REPORT_PATH = BACKEND_ROOT / "evaluation" / "plant_classifier_test_corrective_report.json"
TEST_PREDICTIONS_PATH = (
    BACKEND_ROOT / "evaluation" / "plant_classifier_test_corrective_predictions.csv"
)


@dataclass(frozen=True)
class PlantThresholds:
    min_confidence: float
    min_margin: float


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def get_plant_thresholds() -> PlantThresholds:
    try:
        document = _read_json(CONFIG_PATH)
        classifier = get_classifier_config()
        recorded_model = document["model"]
        if document["status"] not in {
            "corrective_frozen_before_test",
            "candidate_frozen_before_test",
        }:
            raise ValueError("Threshold configuration is not frozen before Test")
        if recorded_model["sha256"] != classifier.sha256:
            raise ValueError("Threshold model checksum does not match runtime model")
        if tuple(recorded_model["class_order"]) != classifier.class_order:
            raise ValueError("Threshold class order does not match runtime model")
        recorded_contract = recorded_model.get("input_contract")
        expected_contract = {
            "decoder": classifier.decoder,
            "resize_method": classifier.resize_method,
            "channels": 3,
            "expand_animations": False,
            "target_size": list(classifier.input_shape[:2]),
            "dtype": "float32",
            "pixel_range": [0, 255],
            "external_normalization": False,
            "preprocessing": classifier.preprocessing,
        }
        if recorded_contract != expected_contract:
            raise ValueError(
                "Threshold input contract does not match runtime preprocessing"
            )
        confidence = float(document["thresholds"]["min_confidence"])
        margin = float(document["thresholds"]["min_margin"])
        if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in (confidence, margin)):
            raise ValueError("Thresholds must be finite values in [0, 1]")
        if REQUIRE_TEST_RECEIPT:
            receipt = _read_json(RECEIPT_PATH)
            expected_receipt_status = (
                "candidate_test_completed"
                if document["status"] == "candidate_frozen_before_test"
                else "corrective_test_completed"
            )
            if receipt["status"] != expected_receipt_status:
                raise ValueError("Test evaluation receipt is incomplete")
            if receipt["frozen_config_sha256"] != _sha256_file(CONFIG_PATH):
                raise ValueError(
                    "Test receipt does not match frozen configuration"
                )
            if receipt["thresholds"] != document["thresholds"]:
                raise ValueError("Test evaluation did not use the frozen thresholds")
            if receipt["threshold_selection_performed_on_test"] is not False:
                raise ValueError("Test receipt permits threshold selection")
            expected_artifacts = {
                "test_report": TEST_REPORT_PATH,
                "test_predictions": TEST_PREDICTIONS_PATH,
            }
            for name, active_path in expected_artifacts.items():
                artifact = receipt["artifacts"][name]
                if document["status"] == "corrective_frozen_before_test":
                    path = active_path
                    if (
                        Path(artifact["path"]).as_posix()
                        != path.relative_to(BACKEND_ROOT).as_posix()
                    ):
                        raise ValueError(
                            f"Unexpected corrective artifact path for {name}"
                        )
                else:
                    path = (BACKEND_ROOT / str(artifact["path"])).resolve()
                    if BACKEND_ROOT not in path.parents:
                        raise ValueError(
                            f"Candidate Test artifact is outside backend for {name}"
                        )
                if artifact["sha256"] != _sha256_file(path):
                    raise ValueError(f"Test artifact checksum mismatch for {name}")
        return PlantThresholds(confidence, margin)
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        raise ValueError("Plant threshold configuration is unavailable") from error
