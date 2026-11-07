from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
import tensorflow as tf
from PIL import Image

from app.schemas.analyze import AnalyzeResponse, DiseasePrediction, PlantPrediction
from app.services.image_service import ValidatedImage
from app.services.plant_classifier_service import (
    PlantClassPrediction,
    PlantClassifierService,
    get_plant_classifier_service,
)
from app.services.model_registry import get_classifier_config
from app.services.threshold_config import PlantThresholds
import app.services.analysis_router as router


def image(filename: str = "leaf.jpg") -> ValidatedImage:
    buffer = BytesIO()
    Image.new("RGB", (16, 16), color=(30, 100, 40)).save(buffer, format="JPEG")
    payload = buffer.getvalue()
    return ValidatedImage(filename, "image/jpeg", "JPEG", len(payload), 16, 16, payload)


def prediction(plant: str, confidence: float, margin: float) -> PlantClassPrediction:
    classes = get_classifier_config().class_order
    return PlantClassPrediction(plant, classes.index(plant), confidence, margin, {name: 0.0 for name in classes})


class FakeClassifier:
    def __init__(self, predictions) -> None:
        self.predictions = tuple(predictions)

    def predict_many(self, _images):
        return self.predictions


class FakeDiseaseService:
    def __init__(self, plant_code: str) -> None:
        self.plant_code = plant_code
        self.calls = []

    def analyze(self, images, confidence: float) -> AnalyzeResponse:
        self.calls.append((images, confidence))
        disease = DiseasePrediction(code="Healthy", name_th="", name_en="Healthy", confidence=0.9)
        return AnalyzeResponse(
            image_count=len(images),
            plant=PlantPrediction(code=self.plant_code, name_th="", name_en="", confidence=confidence),
            disease=disease,
            symptoms=[], care=[], prevention=[], image_results=[],
        )


def arrange(monkeypatch, predictions, thresholds=PlantThresholds(0.8, 0.4)):
    services = {}
    monkeypatch.setattr(router, "get_plant_classifier_service", lambda: FakeClassifier(predictions))
    monkeypatch.setattr(router, "get_plant_thresholds", lambda: thresholds)

    def service(plant_code):
        services.setdefault(plant_code, FakeDiseaseService(plant_code))
        return services[plant_code]

    monkeypatch.setattr(router, "get_model_service", service)
    return services


def test_router_selects_matching_disease_model_and_uses_minimum_confidence(monkeypatch) -> None:
    predictions = [prediction("rose", 0.91, 0.6), prediction("rose", 0.87, 0.5)]
    services = arrange(monkeypatch, predictions)
    result = router.analyze_automatically([image("a.jpg"), image("b.jpg")])
    assert result.status == "completed"
    assert result.plant.code == "rose"
    assert result.plant.confidence == 0.87
    assert list(services) == ["rose"]


def test_threshold_boundary_is_inclusive(monkeypatch) -> None:
    services = arrange(monkeypatch, [prediction("marigold", 0.8, 0.4)])
    result = router.analyze_automatically([image()])
    assert result.status == "completed"
    assert "marigold" in services


@pytest.mark.parametrize(
    ("confidence", "margin", "reason"),
    [(0.799, 0.5, "low_confidence"), (0.9, 0.399, "low_margin")],
)
def test_low_score_requires_manual_confirmation_and_skips_disease_model(
    monkeypatch, confidence: float, margin: float, reason: str
) -> None:
    services = arrange(monkeypatch, [prediction("rose", confidence, margin)])
    result = router.analyze_automatically([image()])
    assert result.status == "manual_confirmation_required"
    assert reason in result.reasons
    assert services == {}


def test_different_plants_require_confirmation_and_no_suggestion(monkeypatch) -> None:
    services = arrange(
        monkeypatch,
        [prediction("rose", 0.95, 0.8), prediction("marigold", 0.96, 0.8)],
    )
    result = router.analyze_automatically([image("a.jpg"), image("b.jpg")])
    assert result.status == "manual_confirmation_required"
    assert result.reasons == ["inconsistent_plant"]
    assert result.suggested_plant is None
    assert all(not item.accepted for item in result.image_predictions)
    assert services == {}


def test_explicit_confirmation_bypasses_classifier(monkeypatch) -> None:
    service = FakeDiseaseService("snake_plant")
    monkeypatch.setattr(router, "get_model_service", lambda _plant: service)
    result = router.analyze_confirmed([image()], "snake_plant")
    assert result.plant.code == "snake_plant"
    assert result.plant.confidence == 1.0


class FakeModel:
    input_shape = (None, 224, 224, 3)
    output_shape = (None, 6)

    def __init__(self, rows) -> None:
        self.rows = np.asarray(rows, dtype=np.float32)

    def __call__(self, _batch, training=False):
        return self.rows


def test_classifier_mapping_margin_and_single_batch_integration() -> None:
    rows = [[0.01, 0.02, 0.03, 0.9, 0.03, 0.01]]
    service = PlantClassifierService(get_classifier_config(), model=FakeModel(rows))
    result = service.predict_many([image()])[0]
    assert result.plant_code == "rose"
    assert result.class_index == 3
    assert result.confidence == pytest.approx(0.9)
    assert result.margin == pytest.approx(0.87)


def test_classifier_rejects_invalid_probability_output() -> None:
    service = PlantClassifierService(
        get_classifier_config(), model=FakeModel([[0.5, 0.5, 0.5, 0.5, 0.5, 0.5]])
    )
    from app.services.plant_classifier_service import ClassifierInferenceError

    with pytest.raises(ClassifierInferenceError):
        service.predict_many([image()])


def test_real_plant_classifier_loads_once_and_matches_manifest() -> None:
    get_plant_classifier_service.cache_clear()
    service = get_plant_classifier_service()
    assert service.model.output_shape[-1] == 6
    assert service.model is service.model
    assert service.load_count == 1
    result = service.predict_many([image()])[0]
    assert result.plant_code in service.class_names
    assert 0.0 <= result.margin <= 1.0


@pytest.mark.parametrize("plant_code", [None, "rose"])
def test_runtime_preprocessing_is_tensor_identical_to_notebook(plant_code: str | None) -> None:
    validated = image()
    decoded = tf.io.decode_image(
        tf.convert_to_tensor(validated.content, dtype=tf.string),
        channels=3,
        expand_animations=False,
    )
    decoded.set_shape([None, None, 3])
    expected = np.asarray(
        tf.image.resize(tf.cast(decoded, tf.float32), [224, 224]), dtype=np.float32
    )
    if plant_code is None:
        service = PlantClassifierService(
            get_classifier_config(), model=FakeModel([[1, 0, 0, 0, 0, 0]])
        )
    else:
        from app.services.plant_model_service import PlantModelService
        from app.services.model_registry import get_plant_config

        class DiseaseFakeModel(FakeModel):
            output_shape = (None, 8)

        service = PlantModelService(
            get_plant_config(plant_code),
            model=DiseaseFakeModel([[1, 0, 0, 0, 0, 0, 0, 0]]),
        )
    np.testing.assert_array_equal(service._prepare(validated), expected)
