from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.image_service import ValidatedImage
from app.services.model_registry import get_classifier_config, get_plant_config
from app.services.plant_classifier_service import get_plant_classifier_service
from app.services.plant_model_service import get_model_service
from app.services.threshold_config import get_plant_thresholds


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path) -> None:
    previous_path = app.state.database_path
    app.state.database_path = tmp_path / "runtime-smoke.db"
    yield
    app.state.database_path = previous_path


def upload() -> tuple[str, bytes, str]:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), color=(45, 120, 55)).save(buffer, format="JPEG")
    return ("leaf.jpg", buffer.getvalue(), "image/jpeg")


def validated_image() -> ValidatedImage:
    filename, content, content_type = upload()
    return ValidatedImage(
        filename=filename,
        content_type=content_type,
        image_format="JPEG",
        size_bytes=len(content),
        width=32,
        height=32,
        content=content,
    )


def test_all_seven_runtime_models_load_and_infer() -> None:
    image = validated_image()
    classifier = get_plant_classifier_service()
    plant_prediction = classifier.predict_many([image])[0]
    assert plant_prediction.plant_code in classifier.class_names
    assert classifier.load_count == 1

    for plant_code in get_classifier_config().class_order:
        config = get_plant_config(plant_code)
        service = get_model_service(plant_code)
        disease_prediction = service.predict(image)
        assert disease_prediction.class_name in config.class_order
        assert service.class_names == config.class_order
        assert service.load_count == 1


def test_automatic_runtime_uses_completed_corrective_evaluation() -> None:
    get_plant_thresholds.cache_clear()
    response = client.post("/api/v1/analyze", files={"images": upload()})
    assert response.status_code == 200
    assert response.json()["status"] in {"completed", "manual_confirmation_required"}


def test_manually_confirmed_supported_plant_still_runs_real_disease_model() -> None:
    response = client.post(
        "/api/v1/analyze",
        data={"plant_code": "rose"},
        files={"images": upload()},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["plant"]["code"] == "rose"
    assert response.json()["plant"]["confidence"] == 1.0
