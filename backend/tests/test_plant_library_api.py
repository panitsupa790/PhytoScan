from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_plant_library_list_and_detail(tmp_path: Path) -> None:
    original_path = app.state.database_path
    app.state.database_path = tmp_path / "plant-library.db"
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/plant-library")
            assert response.status_code == 200
            plants = response.json()["plants"]
            assert [plant["plant_code"] for plant in plants] == [
                "chrysanthemum",
                "marigold",
                "money_plant",
                "rose",
                "snake_plant",
                "spider_plant",
            ]
            assert sum(plant["supported_disease_count"] for plant in plants) == 23

            detail = client.get("/api/v1/plant-library/marigold")
            assert detail.status_code == 200
            body = detail.json()
            assert body["plant_code"] == "marigold"
            assert body["taxonomy"]["scientific_name"] == "Tagetes erecta"
            assert body["review"]["reviewed_by"] == ""
            assert body["review"]["reviewed_at"] is None

            missing = client.get("/api/v1/plant-library/sunflower")
            assert missing.status_code == 404
            assert missing.json()["error_code"] == "PLANT_LIBRARY_NOT_FOUND"
    finally:
        app.state.database_path = original_path
