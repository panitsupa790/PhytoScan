from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.db.database import resolve_database_path
from app.main import app
from app.schemas.analyze import (
    AnalyzeResponse,
    DiseasePrediction,
    ImageAnalyzeResult,
    PlantPrediction,
)


DEVICE_A = "device-test-00000001"
DEVICE_B = "device-test-00000002"


def _upload() -> tuple[str, bytes, str]:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color=(52, 120, 48)).save(buffer, format="JPEG")
    return ("leaf.jpg", buffer.getvalue(), "image/jpeg")


def _completed(images) -> AnalyzeResponse:
    plant = PlantPrediction(
        code="rose", name_th="กุหลาบ", name_en="Rose", confidence=0.95
    )
    disease = DiseasePrediction(
        code="Rose_Healthy",
        name_th="",
        name_en="Healthy Rose",
        confidence=0.84,
    )
    return AnalyzeResponse(
        image_count=len(images),
        plant=plant,
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


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    previous_path = app.state.database_path
    app.state.database_path = tmp_path / "history-api.db"
    monkeypatch.setattr(
        "app.api.routes.analyze.analyze_automatically", _completed
    )
    with TestClient(app) as test_client:
        yield test_client
    app.state.database_path = previous_path
    assert resolve_database_path(previous_path).exists()


def _scan(client: TestClient, device_id: str = DEVICE_A) -> str:
    response = client.post(
        "/api/v1/analyze",
        headers={"X-Device-ID": device_id},
        files={"images": _upload()},
    )
    assert response.status_code == 200
    return response.headers["X-Scan-ID"]


def test_history_requires_an_owner(client: TestClient) -> None:
    response = client.get("/api/v1/history")
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTHENTICATION_REQUIRED"


def test_device_can_list_and_read_only_its_history(client: TestClient) -> None:
    scan_id = _scan(client)
    response = client.get(
        "/api/v1/history", headers={"X-Device-ID": DEVICE_A}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == scan_id
    assert body["items"][0]["plant_code"] == "rose"
    assert body["items"][0]["disease_code"] == "Rose_Healthy"

    detail = client.get(
        f"/api/v1/history/{scan_id}", headers={"X-Device-ID": DEVICE_A}
    )
    assert detail.status_code == 200
    assert detail.json()["image_results"][0]["filename"] == "leaf.jpg"

    other = client.get(
        f"/api/v1/history/{scan_id}", headers={"X-Device-ID": DEVICE_B}
    )
    assert other.status_code == 404


def test_history_delete_is_owner_scoped_and_soft(client: TestClient) -> None:
    scan_id = _scan(client)
    forbidden = client.delete(
        f"/api/v1/history/{scan_id}", headers={"X-Device-ID": DEVICE_B}
    )
    assert forbidden.status_code == 404
    deleted = client.delete(
        f"/api/v1/history/{scan_id}", headers={"X-Device-ID": DEVICE_A}
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] == 1
    history = client.get(
        "/api/v1/history", headers={"X-Device-ID": DEVICE_A}
    ).json()
    assert history["total"] == 0


def test_clear_history_does_not_clear_another_device(client: TestClient) -> None:
    _scan(client, DEVICE_A)
    _scan(client, DEVICE_A)
    _scan(client, DEVICE_B)
    response = client.delete(
        "/api/v1/history", headers={"X-Device-ID": DEVICE_A}
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
    remaining = client.get(
        "/api/v1/history", headers={"X-Device-ID": DEVICE_B}
    ).json()
    assert remaining["total"] == 1
