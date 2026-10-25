from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.services.disease_catalog import load_disease_catalog
from app.services.image_service import ValidatedImage
from app.services.model_registry import get_plant_config, get_registry
from app.services.plant_model_service import (
    InferenceError,
    PlantModelService,
    get_model_service,
)


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
    return ValidatedImage(
        filename="leaf.jpg",
        content_type="image/jpeg",
        image_format="JPEG",
        size_bytes=len(payload),
        width=32,
        height=18,
        content=payload,
    )


def test_registry_preserves_exact_class_order() -> None:
    registry = get_registry()
    assert registry["rose"].class_order == (
        "Rose_Yellow_Mosaic_Virus",
        "Rose_Rust",
        "Rose_Powdery_Mildew",
        "Rose_Mosaic_Virus",
        "Rose_Insect_Damage",
        "Rose_Healthy",
        "Rose_Downy_Mildew",
        "Rose_Black_Spot",
    )
    assert registry["sunflower"].class_order == (
        "downy_mildew",
        "gray_mold",
        "healthy",
        "leaf_scars",
    )


def test_catalog_has_an_entry_for_every_model_class() -> None:
    registry = get_registry()
    catalog = load_disease_catalog()
    for plant_code, config in registry.items():
        assert set(catalog[plant_code]) == set(config.class_order)


def test_direct_resize_keeps_zero_to_255_values() -> None:
    probabilities = [[0.05] * 7 + [0.65]]
    service = PlantModelService(get_plant_config("rose"), model=FakeModel(probabilities))
    prepared = service._prepare(validated_image())
    assert prepared.shape == (224, 224, 3)
    assert prepared.dtype == np.float32
    assert prepared.max() > 1.0


def test_mean_probability_aggregation() -> None:
    rows = [[0.6, 0.2, 0.1, 0.1], [0.2, 0.6, 0.1, 0.1]]
    model = FakeModel(rows)
    service = PlantModelService(get_plant_config("sunflower"), model=model)
    result = service.predict_many([validated_image(), validated_image()])
    assert model.calls == 1
    assert result.aggregation == "mean_class_probabilities"
    assert list(result.probabilities.values()) == pytest.approx(np.mean(rows, axis=0))


def test_analyze_exposes_one_result_per_image_without_second_model_call() -> None:
    rows = [[0.7, 0.1, 0.1, 0.1], [0.1, 0.7, 0.1, 0.1]]
    model = FakeModel(rows)
    service = PlantModelService(get_plant_config("sunflower"), model=model)
    response = service.analyze([validated_image(), validated_image()])
    assert model.calls == 1
    assert [item.index for item in response.image_results] == [0, 1]
    assert [item.disease.code for item in response.image_results] == [
        "downy_mildew",
        "gray_mold",
    ]


def test_invalid_probabilities_are_rejected() -> None:
    model = FakeModel([[0.4, 0.4, 0.4, 0.4]])
    service = PlantModelService(get_plant_config("sunflower"), model=model)
    with pytest.raises(InferenceError):
        service.predict(validated_image())


@pytest.mark.parametrize(("plant_code", "output_count"), [("rose", 8), ("sunflower", 4)])
def test_real_models_load_once_and_match_manifest(plant_code: str, output_count: int) -> None:
    get_model_service.cache_clear()
    service = get_model_service(plant_code)
    assert service.model.output_shape[-1] == output_count
    assert service.model is service.model
    assert service.load_count == 1
    prediction = service.predict(validated_image())
    assert prediction.class_name in service.class_names
    assert sum(prediction.probabilities.values()) == pytest.approx(1.0, abs=1e-5)
