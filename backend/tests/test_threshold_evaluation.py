import hashlib
import json
import numpy as np
import pytest
from types import SimpleNamespace

import scripts.evaluate_plant_classifier as evaluation
import app.services.threshold_config as threshold_config
from scripts.evaluate_plant_classifier import (
    metrics_for_mask,
    observed_candidates,
    select_thresholds,
)


def test_candidates_use_float32_nextafter_and_bounds() -> None:
    value = np.float32(0.5)
    candidates = observed_candidates(np.asarray([value, np.nan, np.inf], dtype=np.float32))
    assert np.float32(0.0) in candidates
    assert np.float32(1.0) in candidates
    assert np.nextafter(value, np.float32(np.inf), dtype=np.float32) in candidates
    assert np.isfinite(candidates).all()
    assert ((candidates >= 0.0) & (candidates <= 1.0)).all()


def test_conservative_selection_prefers_zero_errors_then_coverage() -> None:
    labels = np.asarray([0, 0, 1, 1], dtype=np.int64)
    predictions = np.asarray([0, 1, 1, 1], dtype=np.int64)
    confidence = np.asarray([0.9, 0.6, 0.8, 0.7], dtype=np.float32)
    margin = np.asarray([0.8, 0.1, 0.7, 0.6], dtype=np.float32)
    min_confidence, min_margin = select_thresholds(
        labels, predictions, confidence, margin, class_count=2
    )
    accepted = (confidence >= min_confidence) & (margin >= min_margin)
    assert int((accepted & (predictions != labels)).sum()) == 0
    assert int(accepted.sum()) == 3
    assert all(np.any(accepted & (labels == index)) for index in range(2))


def test_metric_denominators_and_na_values() -> None:
    metrics = metrics_for_mask(
        np.asarray([True, False, True]), np.asarray([False, False, False])
    )
    assert metrics["coverage"] == {"numerator": 0, "denominator": 3, "percentage": 0.0}
    assert metrics["accepted_accuracy"]["percentage"] is None
    assert metrics["false_acceptance_rate_among_incorrect_predictions"]["denominator"] == 1
    assert metrics["correct_rejections"]["numerator"] == 1
    assert metrics["wrongful_rejections"] == {"numerator": 2, "denominator": 2, "percentage": 100.0}


def test_test_evaluation_refuses_to_overwrite_existing_report(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(evaluation, "REPORT_DIR", tmp_path)
    (tmp_path / "plant_classifier_test_report.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="one-time evaluation"):
        evaluation.run_test(SimpleNamespace())


def test_corrective_test_refuses_to_overwrite_existing_artifact(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(evaluation, "CORRECTIVE_TEST_JSON", tmp_path / "test.json")
    monkeypatch.setattr(evaluation, "CORRECTIVE_TEST_MD", tmp_path / "test.md")
    monkeypatch.setattr(evaluation, "CORRECTIVE_TEST_ROWS", tmp_path / "test.csv")
    monkeypatch.setattr(evaluation, "CORRECTIVE_RECEIPT_PATH", tmp_path / "receipt.json")
    (tmp_path / "test.csv").write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to repeat or overwrite"):
        evaluation.run_corrective_test(SimpleNamespace())


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_runtime_rejects_corrective_receipt_for_different_frozen_config(
    tmp_path, monkeypatch
) -> None:
    classifier = threshold_config.get_classifier_config()
    config_path = tmp_path / "config.json"
    receipt_path = tmp_path / "receipt.json"
    report_path = tmp_path / "evaluation" / "report.json"
    predictions_path = tmp_path / "evaluation" / "predictions.csv"
    report_path.parent.mkdir()
    report_path.write_text("{}\n", encoding="utf-8")
    predictions_path.write_text("row_index\n", encoding="utf-8")
    document = {
        "status": "corrective_frozen_before_test",
        "thresholds": {"min_confidence": 0.1, "min_margin": 0.2},
        "model": {
            "sha256": classifier.sha256,
            "class_order": list(classifier.class_order),
            "input_contract": {
                "decoder": classifier.decoder,
                "resize_method": classifier.resize_method,
                "channels": 3,
                "expand_animations": False,
                "target_size": list(classifier.input_shape[:2]),
                "dtype": "float32",
                "pixel_range": [0, 255],
                "external_normalization": False,
                "preprocessing": classifier.preprocessing,
            },
        },
    }
    config_path.write_text(json.dumps(document), encoding="utf-8")
    receipt = {
        "status": "corrective_test_completed",
        "frozen_config_sha256": "0" * 64,
        "thresholds": document["thresholds"],
        "threshold_selection_performed_on_test": False,
        "artifacts": {
            "test_report": {
                "path": "evaluation/report.json",
                "sha256": _sha256(report_path),
            },
            "test_predictions": {
                "path": "evaluation/predictions.csv",
                "sha256": _sha256(predictions_path),
            },
        },
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(threshold_config, "BACKEND_ROOT", tmp_path)
    monkeypatch.setattr(threshold_config, "CONFIG_PATH", config_path)
    monkeypatch.setattr(threshold_config, "RECEIPT_PATH", receipt_path)
    monkeypatch.setattr(threshold_config, "TEST_REPORT_PATH", report_path)
    monkeypatch.setattr(threshold_config, "TEST_PREDICTIONS_PATH", predictions_path)
    threshold_config.get_plant_thresholds.cache_clear()
    with pytest.raises(ValueError, match="does not match frozen configuration"):
        threshold_config.get_plant_thresholds()
    threshold_config.get_plant_thresholds.cache_clear()
