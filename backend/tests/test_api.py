from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.main import app


client = TestClient(app)


def image_bytes(image_format: str = "JPEG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color=(52, 120, 48)).save(buffer, format=image_format)
    return buffer.getvalue()


def upload(filename: str = "leaf.jpg", content_type: str = "image/jpeg"):
    image_format = "PNG" if content_type == "image/png" else "JPEG"
    return (filename, image_bytes(image_format), content_type)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "PhytoScan API"}


def test_analyze_one_jpg() -> None:
    response = client.post("/api/v1/analyze", files={"images": upload()})

    assert response.status_code == 200
    assert response.json()["image_count"] == 1


def test_analyze_one_png() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"images": upload("leaf.png", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["image_count"] == 1


def test_analyze_three_images() -> None:
    files = [("images", upload(f"leaf-{index}.jpg")) for index in range(3)]
    response = client.post("/api/v1/analyze", files=files)

    assert response.status_code == 200
    assert response.json()["image_count"] == 3


def test_rejects_more_than_three_images() -> None:
    files = [("images", upload(f"leaf-{index}.jpg")) for index in range(4)]
    response = client.post("/api/v1/analyze", files=files)

    assert response.status_code == 400
    assert response.json()["error_code"] == "TOO_MANY_IMAGES"


def test_rejects_no_images() -> None:
    response = client.post("/api/v1/analyze")

    assert response.status_code == 400
    assert response.json()["error_code"] == "NO_IMAGES"


def test_rejects_text_file() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"images": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_rejects_fake_jpg() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"images": ("fake.jpg", b"not an image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_IMAGE"


def test_rejects_mismatched_image_metadata() -> None:
    response = client.post(
        "/api/v1/analyze",
        files={"images": ("leaf.jpg", image_bytes("PNG"), "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_IMAGE"


def test_rejects_oversized_file() -> None:
    oversized = b"x" * (settings.max_image_size_bytes + 1)
    response = client.post(
        "/api/v1/analyze",
        files={"images": ("huge.jpg", oversized, "image/jpeg")},
    )

    assert response.status_code == 413
    assert response.json()["error_code"] == "FILE_TOO_LARGE"


def test_success_response_schema() -> None:
    response = client.post("/api/v1/analyze", files={"images": upload()})
    body = response.json()

    assert set(body) == {
        "success",
        "image_count",
        "plant",
        "disease",
        "symptoms",
        "care",
        "prevention",
    }
    assert set(body["plant"]) == {"code", "name_th", "name_en", "confidence"}
    assert set(body["disease"]) == {"code", "name_th", "name_en", "confidence"}


def test_confidence_values_are_normalized() -> None:
    body = client.post("/api/v1/analyze", files={"images": upload()}).json()

    assert 0.0 <= body["plant"]["confidence"] <= 1.0
    assert 0.0 <= body["disease"]["confidence"] <= 1.0


def test_swagger_and_openapi_are_available() -> None:
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/health" in schema["paths"]
    assert "/api/v1/analyze" in schema["paths"]


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
