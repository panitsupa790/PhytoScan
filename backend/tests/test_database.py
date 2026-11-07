from __future__ import annotations

from pathlib import Path

import pytest

from app.db.analysis_repository import record_analysis
from app.db.database import database_connection, initialize_database
from app.schemas.analyze import (
    AnalyzeResponse,
    DiseasePrediction,
    ImageAnalyzeResult,
    ImagePlantPrediction,
    ManualConfirmationResponse,
    PlantPrediction,
)
from app.services.image_service import ValidatedImage


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "phytoscan.db"
    initialize_database(path)
    return path


def image(filename: str = "leaf.jpg") -> ValidatedImage:
    return ValidatedImage(
        filename=filename,
        content_type="image/jpeg",
        image_format="JPEG",
        size_bytes=7,
        width=8,
        height=8,
        content=b"content",
    )


def completed_result(*, confidence: float = 0.95) -> AnalyzeResponse:
    plant = PlantPrediction(
        code="rose", name_th="กุหลาบ", name_en="Rose", confidence=confidence
    )
    disease = DiseasePrediction(
        code="Rose_Healthy",
        name_th="",
        name_en="Healthy Rose",
        confidence=0.84,
    )
    return AnalyzeResponse(
        image_count=1,
        plant=plant,
        disease=disease,
        symptoms=[],
        care=[],
        prevention=[],
        image_results=[
            ImageAnalyzeResult(
                index=0,
                filename="leaf.jpg",
                disease=disease,
                symptoms=[],
                care=[],
                prevention=[],
            )
        ],
    )


def test_migration_and_seed_are_complete_and_idempotent(
    database_path: Path,
) -> None:
    initialize_database(database_path)
    expected_tables = {
        "schema_migrations",
        "users",
        "auth_sessions",
        "devices",
        "plants",
        "plant_library_entries",
        "diseases",
        "disease_guidance",
        "model_artifacts",
        "model_classes",
        "model_thresholds",
        "model_deployments",
        "scan_sessions",
        "scan_images",
        "plant_predictions",
        "plant_prediction_candidates",
        "manual_confirmations",
        "disease_results",
        "result_detail_snapshots",
        "scan_events",
        "scan_errors",
        "user_feedback",
    }
    with database_connection(database_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert expected_tables <= tables
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0] == 3
        plants = [
            row["code"]
            for row in connection.execute(
                "SELECT code FROM plants ORDER BY display_order"
            )
        ]
        assert plants == [
            "chrysanthemum",
            "marigold",
            "money_plant",
            "rose",
            "snake_plant",
            "spider_plant",
        ]
        assert connection.execute("SELECT COUNT(*) FROM diseases").fetchone()[0] == 23
        assert connection.execute(
            "SELECT COUNT(*) FROM plant_library_entries"
        ).fetchone()[0] == 6
        assert connection.execute(
            "SELECT COUNT(*) FROM model_artifacts"
        ).fetchone()[0] == 7
        assert connection.execute("SELECT COUNT(*) FROM model_classes").fetchone()[0] == 29
        assert connection.execute(
            "SELECT COUNT(*) FROM model_deployments"
        ).fetchone()[0] == 7


def test_frozen_threshold_and_model_identity_are_seeded(
    database_path: Path,
) -> None:
    with database_connection(database_path) as connection:
        model = connection.execute(
            """
            SELECT model_version, sha256 FROM model_artifacts
            WHERE model_type = 'plant_classifier' AND is_active = 1
            """
        ).fetchone()
        threshold = connection.execute(
            """
            SELECT min_confidence, min_margin, test_adjustment_performed
            FROM model_thresholds WHERE is_active = 1
            """
        ).fetchone()
        class_order = [
            row["class_code"]
            for row in connection.execute(
                """
                SELECT mc.class_code FROM model_classes mc
                JOIN model_artifacts ma ON ma.id = mc.model_id
                WHERE ma.model_type = 'plant_classifier'
                ORDER BY mc.class_index
                """
            )
        ]
    assert model["model_version"] == "plant-classifier-v1"
    assert model["sha256"] == (
        "5585bb91835006003e6f052c58465d84fc0d9ac6e37227d842a28d18f3991165"
    )
    assert threshold["min_confidence"] == 0.0
    assert threshold["min_margin"] == 0.6936511993408203
    assert threshold["test_adjustment_performed"] == 0
    assert class_order == [
        "chrysanthemum",
        "marigold",
        "money_plant",
        "rose",
        "snake_plant",
        "spider_plant",
    ]


def test_completed_analysis_is_persisted_without_image_bytes(
    database_path: Path,
) -> None:
    scan_id = record_analysis(
        [image()], completed_result(), database_path=database_path
    )
    with database_connection(database_path) as connection:
        session = connection.execute(
            """
            SELECT status, plant_source, plant_confidence, result_agreement
            FROM scan_sessions WHERE id = ?
            """,
            (scan_id,),
        ).fetchone()
        stored_image = connection.execute(
            """
            SELECT local_path, storage_key, sha256
            FROM scan_images WHERE scan_id = ?
            """,
            (scan_id,),
        ).fetchone()
        assert connection.execute(
            "SELECT COUNT(*) FROM disease_results"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM scan_events"
        ).fetchone()[0] == 1
    assert tuple(session) == ("completed", "automatic", 0.95, 1)
    assert stored_image["local_path"] is None
    assert stored_image["storage_key"] is None
    assert len(stored_image["sha256"]) == 64


def test_manual_confirmation_stores_margin_and_skips_disease(
    database_path: Path,
) -> None:
    plant = PlantPrediction(
        code="rose", name_th="กุหลาบ", name_en="Rose", confidence=0.60
    )
    result = ManualConfirmationResponse(
        message="confirm",
        suggested_plant=plant,
        image_predictions=[
            ImagePlantPrediction(
                index=0,
                filename="leaf.jpg",
                plant=plant,
                margin=0.10,
                accepted=False,
                reasons=["low_margin"],
            )
        ],
        reasons=["low_margin"],
    )
    scan_id = record_analysis([image()], result, database_path=database_path)
    with database_connection(database_path) as connection:
        status = connection.execute(
            "SELECT status FROM scan_sessions WHERE id = ?", (scan_id,)
        ).fetchone()["status"]
        prediction = connection.execute(
            """
            SELECT confidence, top1_top2_margin, accepted, decision
            FROM plant_predictions
            """
        ).fetchone()
        disease_count = connection.execute(
            "SELECT COUNT(*) FROM disease_results"
        ).fetchone()[0]
        confirmation_count = connection.execute(
            "SELECT COUNT(*) FROM manual_confirmations"
        ).fetchone()[0]
    assert status == "manual_confirmation_required"
    assert tuple(prediction) == (0.60, 0.10, 0, "low_margin")
    assert disease_count == 0
    assert confirmation_count == 1


def test_manual_selection_is_not_stored_as_ai_confidence_100_percent(
    database_path: Path,
) -> None:
    result = completed_result(confidence=1.0)
    scan_id = record_analysis(
        [image()], result, "rose", database_path=database_path
    )
    with database_connection(database_path) as connection:
        session = connection.execute(
            """
            SELECT plant_source, plant_confidence
            FROM scan_sessions WHERE id = ?
            """,
            (scan_id,),
        ).fetchone()
        prediction = connection.execute(
            "SELECT confidence, decision FROM plant_predictions"
        ).fetchone()
    assert tuple(session) == ("manual_selection", None)
    assert tuple(prediction) == (None, "manual_selection")
