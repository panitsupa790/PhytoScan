from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.services.disease_catalog import load_disease_catalog
from app.services.image_service import ValidatedImage
from app.services.model_registry import get_classifier_config, get_plant_config, get_registry
from app.services.plant_model_service import InferenceError, PlantModelService, get_model_service


class FakeModel:
    input_shape = (None, 224, 224, 3)

    def __init__(self, probabilities: list[list[float]]) -> None:
        self.probabilities = np.asarray(probabilities, dtype=np.float32)
        self.output_shape = (None, self.probabilities.shape[-1])
        self.calls = 0

    def __call__(self, batch: np.ndarray, training: bool = False) -> np.ndarray:
        assert training is False
        self.calls += 1
        if len(self.probabilities) == 1:
            return np.repeat(self.probabilities, len(batch), axis=0)
        return self.probabilities


def validated_image() -> ValidatedImage:
    buffer = BytesIO()
    Image.new("RGB", (32, 18), color=(70, 125, 52)).save(buffer, format="JPEG")
    payload = buffer.getvalue()
    return ValidatedImage("leaf.jpg", "image/jpeg", "JPEG", len(payload), 32, 18, payload)


def test_registry_and_classifier_preserve_exact_class_orders() -> None:
    classifier = get_classifier_config()
    assert classifier.class_order == (
        "chrysanthemum", "marigold", "money_plant", "rose", "snake_plant", "spider_plant"
    )
    registry = get_registry()
    assert tuple(registry) == classifier.class_order
    assert registry["marigold"].class_order == (
        "Alternaria Leaf Blight", "Helathy Leaves", "Pest Damaged"
    )
    assert registry["rose"].class_order[-1] == "Rose_Black_Spot"
    assert "sunflower" not in registry


def test_catalog_has_exact_entry_for_every_active_model_class() -> None:
    catalog = load_disease_catalog()
    for plant_code, config in get_registry().items():
        assert set(catalog[plant_code]) == set(config.class_order)
        for disease in catalog[plant_code].values():
            # Metadata may be populated or intentionally empty, but the API
            # contract always exposes lists and must never invent a fallback.
            assert isinstance(disease["symptoms"], list)
            assert isinstance(disease["care"], list)
            assert isinstance(disease["prevention"], list)
    assert "sunflower" not in catalog


def test_direct_resize_keeps_zero_to_255_values() -> None:
    probabilities = [[0.05] * 7 + [0.65]]
    service = PlantModelService(get_plant_config("rose"), model=FakeModel(probabilities))
    prepared = service._prepare(validated_image())
    assert prepared.shape == (224, 224, 3)
    assert prepared.dtype == np.float32
    assert prepared.max() > 1.0


def test_mean_probability_aggregation_and_single_batch_call() -> None:
    rows = [[0.6, 0.2, 0.2], [0.2, 0.6, 0.2]]
    model = FakeModel(rows)
    service = PlantModelService(get_plant_config("chrysanthemum"), model=model)
    result = service.predict_many([validated_image(), validated_image()])
    assert model.calls == 1
    assert result.aggregation == "mean_class_probabilities"
    assert list(result.probabilities.values()) == pytest.approx(np.mean(rows, axis=0))
    response = service.analyze([validated_image(), validated_image()], plant_confidence=0.91)
    assert response.plant.confidence == 0.91
    assert model.calls == 2


def test_invalid_probabilities_are_rejected() -> None:
    service = PlantModelService(
        get_plant_config("chrysanthemum"), model=FakeModel([[0.4, 0.4, 0.4]])
    )
    with pytest.raises(InferenceError):
        service.predict(validated_image())


@pytest.mark.parametrize(
    ("plant_code", "output_count"),
    [
        ("chrysanthemum", 3),
        ("marigold", 3),
        ("money_plant", 3),
        ("rose", 8),
        ("snake_plant", 3),
        ("spider_plant", 3),
    ],
)
def test_real_disease_models_load_and_match_manifest(plant_code: str, output_count: int) -> None:
    get_model_service.cache_clear()
    service = get_model_service(plant_code)
    assert service.model.output_shape[-1] == output_count
    assert service.model is service.model
    assert service.load_count == 1
    prediction = service.predict(validated_image())
    assert prediction.class_name in service.class_names
    assert sum(prediction.probabilities.values()) == pytest.approx(1.0, abs=1e-5)
