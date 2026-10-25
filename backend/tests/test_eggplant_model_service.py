from __future__ import annotations

import hashlib
import importlib
import json
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.services.eggplant_model_service import (
    EggplantModelService,
    InferenceError,
    get_eggplant_model_service,
)
from app.services.image_service import ValidatedImage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "ai_model/models/eggplant/v1/model_manifest.json"
TRAIN_SAMPLE = PROJECT_ROOT / "dataset/split/eggplant/train/healthy/Healthy Leaf Image 1.jpg"
GOLDEN_PATH = PROJECT_ROOT / "ai_model/experiments/eggplant_backend_d12/golden_regression.json"


class FakeModel:
    input_shape = (None, 224, 224, 3)
    output_shape = (None, 3)

    def __init__(self, probabilities: list[list[float]]) -> None:
        self.probabilities = np.asarray(probabilities, dtype=np.float32)
        self.calls = 0

    def __call__(self, batch: np.ndarray, training: bool = False) -> np.ndarray:
        assert training is False
        self.calls += 1
        if len(self.probabilities) == 1:
            return np.repeat(self.probabilities, len(batch), axis=0)
        assert len(self.probabilities) == len(batch)
        return self.probabilities


def image_content(color: tuple[int, int, int] = (60, 120, 55)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (16, 12), color=color).save(buffer, format="JPEG")
    return buffer.getvalue()


def validated_image(content: bytes | None = None, filename: str = "leaf.jpg") -> ValidatedImage:
    payload = content if content is not None else image_content()
    return ValidatedImage(
        filename=filename,
        content_type="image/jpeg",
        image_format="JPEG",
        size_bytes=len(payload),
        width=16,
        height=12,
        content=payload,
    )


def fake_service(probabilities: list[list[float]]) -> tuple[EggplantModelService, FakeModel]:
    model = FakeModel(probabilities)
    return EggplantModelService(MANIFEST_PATH, model=model), model


@pytest.mark.parametrize(
    ("probabilities", "expected_index", "expected_class"),
    [
        ([0.8, 0.1, 0.1], 0, "healthy"),
        ([0.1, 0.8, 0.1], 1, "leaf_spot"),
        ([0.1, 0.2, 0.7], 2, "mosaic_virus"),
    ],
)
def test_class_mapping(probabilities, expected_index, expected_class) -> None:
    service, _ = fake_service([probabilities])
    prediction = service.predict(validated_image())
    assert prediction.class_index == expected_index
    assert prediction.class_name == expected_class
    assert prediction.confidence == pytest.approx(max(probabilities))
    assert sum(prediction.probabilities.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("image_count", [1, 2, 3])
def test_one_to_three_image_aggregation_uses_mean_probabilities(image_count: int) -> None:
    rows = [[0.1 + index * 0.05, 0.8 - index * 0.1, 0.1 + index * 0.05] for index in range(image_count)]
    service, model = fake_service(rows)
    result = service.predict_many([validated_image(filename=f"leaf-{index}.jpg") for index in range(image_count)])
    expected = np.asarray(rows).mean(axis=0)
    assert model.calls == 1
    assert result.aggregation == "mean_class_probabilities"
    assert result.class_index == int(expected.argmax())
    assert [result.probabilities[name] for name in service.class_names] == pytest.approx(expected)


def test_service_rejects_more_than_three_images() -> None:
    service, _ = fake_service([[0.7, 0.2, 0.1]])
    with pytest.raises(InferenceError):
        service.predict_many([validated_image() for _ in range(4)])


@pytest.mark.parametrize("class_index", [0, 1, 2])
def test_response_uses_catalog_for_every_model_class(class_index: int) -> None:
    probabilities = [0.05, 0.05, 0.05]
    probabilities[class_index] = 0.9
    service, _ = fake_service([probabilities])
    response = service.analyze([validated_image()])
    assert response.plant.code == "eggplant"
    assert response.plant.confidence == 1.0
    assert response.disease.code == service.class_names[class_index]
    assert response.disease.confidence == pytest.approx(0.9)
    assert response.symptoms and response.care and response.prevention
    if response.disease.code == "mosaic_virus":
        assert any("ไม่ใช่การยืนยันเชื้อไวรัส" in item for item in response.symptoms)


def test_backend_preprocessing_is_exact_locked_p3_reuse() -> None:
    service, _ = fake_service([[0.8, 0.1, 0.1]])
    payload = TRAIN_SAMPLE.read_bytes()
    backend_output = service._prepare(validated_image(payload, TRAIN_SAMPLE.name))
    with Image.open(TRAIN_SAMPLE) as source:
        source.load()
        locked_output = service._preprocess(source.convert("RGB"), "P3", service.preprocessing_config)
    expected = np.asarray(locked_output, dtype=np.float32)
    np.testing.assert_array_equal(backend_output, expected)
    assert hashlib.sha256(backend_output.astype(np.uint8).tobytes()).hexdigest() == hashlib.sha256(
        expected.astype(np.uint8).tobytes()
    ).hexdigest()


def test_normal_route_does_not_import_mock_service() -> None:
    route = importlib.import_module("app.api.routes.analyze")
    assert "mock_ai_service" not in route.__dict__


def test_locked_real_model_loads_once_and_runs_train_image() -> None:
    get_eggplant_model_service.cache_clear()
    first = get_eggplant_model_service()
    second = get_eggplant_model_service()
    assert first is second
    assert first.load_count == 1
    payload = TRAIN_SAMPLE.read_bytes()
    prediction = first.predict(validated_image(payload, TRAIN_SAMPLE.name))
    assert prediction.class_name in first.class_names
    assert 0.0 <= prediction.confidence <= 1.0
    assert sum(prediction.probabilities.values()) == pytest.approx(1.0, abs=1e-5)


def test_real_model_matches_validation_golden_probabilities() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    service = get_eggplant_model_service()
    tolerance = golden["probability_tolerance"]
    for sample in golden["samples"]:
        path = PROJECT_ROOT / "dataset/split/eggplant/val" / sample["true_class"] / sample["filename"]
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == sample["input_sha256"]
        prediction = service.predict(validated_image(payload, sample["filename"]))
        assert prediction.class_name == sample["predicted_class"]
        assert [prediction.probabilities[name] for name in service.class_names] == pytest.approx(
            [sample["probabilities"][name] for name in service.class_names], abs=tolerance
        )
