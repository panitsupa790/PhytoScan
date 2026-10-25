from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.schemas.analyze import (
    AnalyzeResponse,
    DiseasePrediction,
    ImageAnalyzeResult,
    PlantPrediction,
)
from app.services.plant_model_service import InferenceError, ModelUnavailableError
from app.main import app


client = TestClient(app)


class FakePlantService:
    def __init__(self, plant_code: str) -> None:
        self.plant_code = plant_code

    def analyze(self, images) -> AnalyzeResponse:
        names = {
            "rose": ("กุหลาบ", "Rose", "Rose_Healthy", "Healthy Rose"),
            "sunflower": ("ทานตะวัน", "Sunflower", "healthy", "Healthy Sunflower"),
        }
        plant_th, plant_en, disease_code, disease_en = names[self.plant_code]
        disease = DiseasePrediction(
            code=disease_code,
            name_th="",
            name_en=disease_en,
            confidence=0.84,
        )
        return AnalyzeResponse(
            image_count=len(images),
            plant=PlantPrediction(
                code=self.plant_code,
                name_th=plant_th,
                name_en=plant_en,
                confidence=1.0,
            ),
            disease=disease,
            symptoms=[],
            care=[],
            prevention=[],
            image_results=[
                ImageAnalyzeResult(
                    index=index,
                    filename=image.filename,
                    disease=disease,
                    symptoms=[],
                    care=[],
                    prevention=[],
                )
                for index, image in enumerate(images)
            ],
        )


@pytest.fixture(autouse=True)
def fake_model_services(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.analyze.get_model_service",
        lambda plant_code: FakePlantService(plant_code),
    )


def image_bytes(image_format: str = "JPEG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color=(52, 120, 48)).save(buffer, format=image_format)
    return buffer.getvalue()


def upload(filename: str = "leaf.jpg", content_type: str = "image/jpeg"):
    image_format = "PNG" if content_type == "image/png" else "JPEG"
    return (filename, image_bytes(image_format), content_type)


def analyze(plant_code: str = "rose", files=None):
    return client.post(
        "/api/v1/analyze",
        data={"plant_code": plant_code},
        files=files if files is not None else {"images": upload()},
    )


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "PhytoScan API"}


def test_supported_plants() -> None:
    response = client.get("/api/v1/plants")
    assert response.status_code == 200
    assert response.json() == {
        "plants": [
            {
                "code": "rose",
                "name_th": "กุหลาบ",
                "name_en": "Rose",
                "disease_count": 8,
            },
            {
                "code": "sunflower",
                "name_th": "ทานตะวัน",
                "name_en": "Sunflower",
                "disease_count": 4,
            },
        ]
    }


@pytest.mark.parametrize(
    ("plant_code", "expected_disease"),
    [("rose", "Rose_Healthy"), ("sunflower", "healthy")],
)
def test_analyze_supported_plant(plant_code: str, expected_disease: str) -> None:
    response = analyze(plant_code)
    assert response.status_code == 200
    assert response.json()["plant"]["code"] == plant_code
    assert response.json()["disease"]["code"] == expected_disease


def test_analyze_three_images_uses_existing_validation() -> None:
    files = [("images", upload(f"leaf-{index}.jpg")) for index in range(3)]
    response = analyze(files=files)
    assert response.status_code == 200
    assert response.json()["image_count"] == 3
    assert [item["index"] for item in response.json()["image_results"]] == [0, 1, 2]
    assert [item["filename"] for item in response.json()["image_results"]] == [
        "leaf-0.jpg",
        "leaf-1.jpg",
        "leaf-2.jpg",
    ]


def test_rejects_unsupported_plant() -> None:
    response = analyze("eggplant")
    assert response.status_code == 400
    assert response.json()["error_code"] == "UNSUPPORTED_PLANT"


def test_rejects_more_than_three_images() -> None:
    files = [("images", upload(f"leaf-{index}.jpg")) for index in range(4)]
    response = analyze(files=files)
    assert response.status_code == 400
    assert response.json()["error_code"] == "TOO_MANY_IMAGES"


def test_rejects_no_images() -> None:
    response = client.post("/api/v1/analyze", data={"plant_code": "rose"})
    assert response.status_code == 400
    assert response.json()["error_code"] == "NO_IMAGES"


def test_rejects_text_file() -> None:
    response = analyze(files={"images": ("notes.txt", b"not an image", "text/plain")})
    assert response.status_code == 415
    assert response.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_rejects_fake_jpg() -> None:
    response = analyze(files={"images": ("fake.jpg", b"not an image", "image/jpeg")})
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_IMAGE"


def test_rejects_mismatched_image_metadata() -> None:
    response = analyze(files={"images": ("leaf.jpg", image_bytes("PNG"), "image/png")})
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_IMAGE"


def test_rejects_oversized_file() -> None:
    oversized = b"x" * (settings.max_image_size_bytes + 1)
    response = analyze(files={"images": ("huge.jpg", oversized, "image/jpeg")})
    assert response.status_code == 413
    assert response.json()["error_code"] == "FILE_TOO_LARGE"


def test_success_response_schema() -> None:
    body = analyze().json()
    assert set(body) == {
        "success",
        "image_count",
        "plant",
        "disease",
        "symptoms",
        "care",
        "prevention",
        "image_results",
    }
    assert set(body["plant"]) == {"code", "name_th", "name_en", "confidence"}
    assert set(body["disease"]) == {"code", "name_th", "name_en", "confidence"}


def test_swagger_and_openapi_are_available() -> None:
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/health" in paths
    assert "/api/v1/plants" in paths
    assert "/api/v1/analyze" in paths


def test_development_cors_origin_is_allowed() -> None:
    response = client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"


def test_model_unavailable_is_sanitized(monkeypatch) -> None:
    def unavailable(_plant_code):
        raise ModelUnavailableError("sensitive internal detail")

    monkeypatch.setattr("app.api.routes.analyze.get_model_service", unavailable)
    response = analyze()
    assert response.status_code == 503
    assert response.json()["error_code"] == "MODEL_UNAVAILABLE"
    assert response.json()["message"] == "Plant analysis model is unavailable"


def test_inference_failure_is_sanitized(monkeypatch) -> None:
    class BrokenService:
        def analyze(self, _images):
            raise InferenceError("sensitive internal detail")

    monkeypatch.setattr(
        "app.api.routes.analyze.get_model_service", lambda _plant_code: BrokenService()
    )
    response = analyze()
    assert response.status_code == 500
    assert response.json()["error_code"] == "INFERENCE_FAILED"
    assert response.json()["message"] == "Plant image analysis failed"
