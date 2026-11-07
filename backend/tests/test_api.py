from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.schemas.analyze import (
    AnalyzeResponse,
    DiseasePrediction,
    ImageAnalyzeResult,
    ImagePlantPrediction,
    ManualConfirmationResponse,
    PlantPrediction,
)
from app.services.plant_classifier_service import (
    ClassifierInferenceError,
    ClassifierUnavailableError,
)
from app.services.plant_model_service import InferenceError, ModelUnavailableError
from app.main import app


client = TestClient(app)


def completed(images, plant_code: str = "rose", confidence: float = 1.0) -> AnalyzeResponse:
    plant = PlantPrediction(code=plant_code, name_th="", name_en=plant_code, confidence=confidence)
    disease = DiseasePrediction(code="Healthy", name_th="", name_en="Healthy", confidence=0.84)
    return AnalyzeResponse(
        image_count=len(images),
        plant=plant,
        disease=disease,
        symptoms=[],
        care=[],
        prevention=[],
        image_results=[
            ImageAnalyzeResult(index=index, filename=image.filename, disease=disease, symptoms=[], care=[], prevention=[])
            for index, image in enumerate(images)
        ],
    )


@pytest.fixture(autouse=True)
def fake_router(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.analyze.analyze_confirmed",
        lambda images, plant_code: completed(images, plant_code),
    )
    monkeypatch.setattr(
        "app.api.routes.analyze.analyze_automatically",
        lambda images: completed(images, "rose", 0.95),
    )
    monkeypatch.setattr(
        "app.api.routes.analyze.record_analysis",
        lambda images, result, plant_code: "test-scan-id",
    )


def image_bytes(image_format: str = "JPEG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color=(52, 120, 48)).save(buffer, format=image_format)
    return buffer.getvalue()


def upload(filename: str = "leaf.jpg", content_type: str = "image/jpeg"):
    image_format = "PNG" if content_type == "image/png" else "JPEG"
    return (filename, image_bytes(image_format), content_type)


def analyze(plant_code: str | None = "rose", files=None):
    data = {} if plant_code is None else {"plant_code": plant_code}
    return client.post(
        "/api/v1/analyze",
        data=data,
        files=files if files is not None else {"images": upload()},
    )


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "PhytoScan API"}


def test_supported_plants_are_the_six_classifier_classes() -> None:
    response = client.get("/api/v1/plants")
    assert response.status_code == 200
    codes = [row["code"] for row in response.json()["plants"]]
    assert codes == ["chrysanthemum", "marigold", "money_plant", "rose", "snake_plant", "spider_plant"]
    assert "sunflower" not in codes


def test_manual_confirmation_preserves_existing_api_flow() -> None:
    response = analyze("snake_plant")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["plant"]["code"] == "snake_plant"
    assert response.json()["plant"]["confidence"] == 1.0


def test_automatic_flow_when_plant_code_is_omitted() -> None:
    response = analyze(None)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["plant"]["code"] == "rose"
    assert response.json()["plant"]["confidence"] == 0.95


def test_manual_confirmation_required_schema(monkeypatch) -> None:
    plant = PlantPrediction(code="rose", name_th="กุหลาบ", name_en="Rose", confidence=0.6)
    result = ManualConfirmationResponse(
        message="confirm",
        suggested_plant=plant,
        image_predictions=[
            ImagePlantPrediction(index=0, filename="leaf.jpg", plant=plant, margin=0.1, accepted=False, reasons=["low_margin"])
        ],
        reasons=["low_margin"],
    )
    monkeypatch.setattr("app.api.routes.analyze.analyze_automatically", lambda _images: result)
    body = analyze(None).json()
    assert body["success"] is False
    assert body["status"] == "manual_confirmation_required"
    assert body["reasons"] == ["low_margin"]
    assert "disease" not in body


def test_three_images_preserve_order() -> None:
    files = [("images", upload(f"leaf-{index}.jpg")) for index in range(3)]
    body = analyze(files=files).json()
    assert body["image_count"] == 3
    assert [item["filename"] for item in body["image_results"]] == ["leaf-0.jpg", "leaf-1.jpg", "leaf-2.jpg"]


def test_rejects_unsupported_manual_plant() -> None:
    response = analyze("sunflower")
    assert response.status_code == 400
    assert response.json()["error_code"] == "UNSUPPORTED_PLANT"


@pytest.mark.parametrize(
    ("files", "status_code", "error_code"),
    [
        ([("images", upload(f"leaf-{index}.jpg")) for index in range(4)], 400, "TOO_MANY_IMAGES"),
        ({"images": ("notes.txt", b"not an image", "text/plain")}, 415, "UNSUPPORTED_FILE_TYPE"),
        ({"images": ("fake.jpg", b"not an image", "image/jpeg")}, 400, "INVALID_IMAGE"),
        ({"images": ("leaf.jpg", image_bytes("PNG"), "image/png")}, 400, "INVALID_IMAGE"),
    ],
)
def test_invalid_uploads(files, status_code: int, error_code: str) -> None:
    response = analyze(files=files)
    assert response.status_code == status_code
    assert response.json()["error_code"] == error_code


def test_rejects_no_images() -> None:
    response = client.post("/api/v1/analyze", data={"plant_code": "rose"})
    assert response.status_code == 400
    assert response.json()["error_code"] == "NO_IMAGES"


def test_rejects_oversized_file() -> None:
    oversized = b"x" * (settings.max_image_size_bytes + 1)
    response = analyze(files={"images": ("huge.jpg", oversized, "image/jpeg")})
    assert response.status_code == 413
    assert response.json()["error_code"] == "FILE_TOO_LARGE"


@pytest.mark.parametrize("error", [ModelUnavailableError("detail"), ClassifierUnavailableError("detail")])
def test_model_unavailable_is_sanitized(monkeypatch, error) -> None:
    def unavailable(_images):
        raise error

    monkeypatch.setattr("app.api.routes.analyze.analyze_automatically", unavailable)
    response = analyze(None)
    assert response.status_code == 503
    assert response.json() == {
        "success": False,
        "error_code": "MODEL_UNAVAILABLE",
        "message": "Plant analysis model is unavailable",
    }


@pytest.mark.parametrize("error", [InferenceError("detail"), ClassifierInferenceError("detail")])
def test_inference_failure_is_sanitized(monkeypatch, error) -> None:
    def broken(_images):
        raise error

    monkeypatch.setattr("app.api.routes.analyze.analyze_automatically", broken)
    response = analyze(None)
    assert response.status_code == 500
    assert response.json()["error_code"] == "INFERENCE_FAILED"
    assert response.json()["message"] == "Plant image analysis failed"


def test_openapi_documents_both_analysis_responses() -> None:
    assert client.get("/docs").status_code == 200
    operation = client.get("/openapi.json").json()["paths"]["/api/v1/analyze"]["post"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert len(schema["anyOf"]) == 2


def test_development_cors_origin_is_allowed() -> None:
    response = client.options(
        "/api/v1/analyze",
        headers={"Origin": "http://localhost:8080", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"
