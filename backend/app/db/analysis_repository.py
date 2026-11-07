from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.db.database import database_connection, initialize_database
from app.schemas.analyze import AnalyzeResponse, ManualConfirmationResponse
from app.services.image_service import ValidatedImage


AnalysisResult = AnalyzeResponse | ManualConfirmationResponse


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _plant_id(connection: object, code: str) -> int:
    row = connection.execute(
        "SELECT id FROM plants WHERE code = ? AND is_active = 1", (code,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Active plant metadata is missing for {code}")
    return int(row["id"])


def _active_model_id(
    connection: object, model_type: str, plant_id: int | None = None
) -> int | None:
    if plant_id is None:
        row = connection.execute(
            """
            SELECT id FROM model_artifacts
            WHERE model_type = ? AND plant_id IS NULL AND is_active = 1
            ORDER BY id DESC LIMIT 1
            """,
            (model_type,),
        ).fetchone()
    else:
        row = connection.execute(
            """
            SELECT id FROM model_artifacts
            WHERE model_type = ? AND plant_id = ? AND is_active = 1
            ORDER BY id DESC LIMIT 1
            """,
            (model_type, plant_id),
        ).fetchone()
    return int(row["id"]) if row is not None else None


def _insert_images(
    connection: object,
    scan_id: str,
    images: Sequence[ValidatedImage],
    now: str,
) -> dict[int, int]:
    image_ids: dict[int, int] = {}
    for index, image in enumerate(images):
        cursor = connection.execute(
            """
            INSERT INTO scan_images(
                scan_id, image_index, original_filename, mime_type,
                file_size, width, height, sha256, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                index,
                image.filename,
                image.content_type,
                image.size_bytes,
                image.width,
                image.height,
                hashlib.sha256(image.content).hexdigest(),
                now,
            ),
        )
        image_ids[index] = int(cursor.lastrowid)
    return image_ids


def _insert_prediction(
    connection: object,
    *,
    scan_image_id: int,
    model_id: int | None,
    plant_id: int,
    plant_code: str,
    confidence: float | None,
    margin: float | None,
    accepted: bool,
    decision: str,
    reasons: Sequence[str],
    now: str,
) -> None:
    connection.execute(
        """
        INSERT INTO plant_predictions(
            scan_image_id, model_id, predicted_plant_id,
            predicted_code_snapshot, confidence, top1_top2_margin,
            accepted, decision, rejection_reasons, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scan_image_id,
            model_id,
            plant_id,
            plant_code,
            confidence,
            margin,
            int(accepted),
            decision,
            _json(list(reasons)),
            now,
        ),
    )


def _record_completed(
    connection: object,
    scan_id: str,
    image_ids: dict[int, int],
    result: AnalyzeResponse,
    requested_plant_code: str | None,
    now: str,
) -> None:
    plant_id = _plant_id(connection, result.plant.code)
    automatic = requested_plant_code is None
    plant_model_id = (
        _active_model_id(connection, "plant_classifier") if automatic else None
    )
    plant_source = "automatic" if automatic else "manual_selection"
    stored_plant_confidence = result.plant.confidence if automatic else None
    disease_codes = {item.disease.code for item in result.image_results}
    result_agreement = len(disease_codes) <= 1
    connection.execute(
        """
        UPDATE scan_sessions SET
            status = 'completed', final_plant_id = ?,
            plant_name_th_snapshot = ?, plant_name_en_snapshot = ?,
            plant_confidence = ?, plant_source = ?, result_agreement = ?,
            plant_classifier_model_id = ?, completed_at = ?
        WHERE id = ?
        """,
        (
            plant_id,
            result.plant.name_th,
            result.plant.name_en,
            stored_plant_confidence,
            plant_source,
            int(result_agreement),
            plant_model_id,
            now,
            scan_id,
        ),
    )

    for index in image_ids:
        _insert_prediction(
            connection,
            scan_image_id=image_ids[index],
            model_id=plant_model_id,
            plant_id=plant_id,
            plant_code=result.plant.code,
            confidence=stored_plant_confidence,
            margin=None,
            accepted=True,
            decision="accepted" if automatic else "manual_selection",
            reasons=(),
            now=now,
        )

    disease_model_id = _active_model_id(
        connection, "disease_classifier", plant_id
    )
    for image_result in result.image_results:
        disease = connection.execute(
            "SELECT id, is_healthy FROM diseases WHERE plant_id = ? AND code = ?",
            (plant_id, image_result.disease.code),
        ).fetchone()
        disease_id = int(disease["id"]) if disease is not None else None
        is_healthy = int(disease["is_healthy"]) if disease is not None else 0
        cursor = connection.execute(
            """
            INSERT INTO disease_results(
                scan_image_id, plant_id, disease_id, disease_model_id,
                disease_code_snapshot, disease_name_th_snapshot,
                disease_name_en_snapshot, confidence, is_healthy,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?)
            """,
            (
                image_ids[image_result.index],
                plant_id,
                disease_id,
                disease_model_id,
                image_result.disease.code,
                image_result.disease.name_th,
                image_result.disease.name_en,
                image_result.disease.confidence,
                is_healthy,
                now,
            ),
        )
        disease_result_id = int(cursor.lastrowid)
        for detail_type, values in (
            ("symptom", image_result.symptoms),
            ("care", image_result.care),
            ("prevention", image_result.prevention),
        ):
            for sort_order, content in enumerate(values):
                connection.execute(
                    """
                    INSERT INTO result_detail_snapshots(
                        disease_result_id, detail_type, content, sort_order
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (disease_result_id, detail_type, content, sort_order),
                )
    connection.execute(
        """
        INSERT INTO scan_events(scan_id, event_type, event_data, created_at)
        VALUES (?, 'analysis_completed', ?, ?)
        """,
        (
            scan_id,
            _json(
                {
                    "plant_code": result.plant.code,
                    "plant_source": plant_source,
                    "result_agreement": result_agreement,
                }
            ),
            now,
        ),
    )


def _record_manual_confirmation(
    connection: object,
    scan_id: str,
    image_ids: dict[int, int],
    result: ManualConfirmationResponse,
    now: str,
) -> None:
    plant_model_id = _active_model_id(connection, "plant_classifier")
    suggested_id = (
        _plant_id(connection, result.suggested_plant.code)
        if result.suggested_plant is not None
        else None
    )
    connection.execute(
        """
        UPDATE scan_sessions SET
            status = 'manual_confirmation_required',
            plant_classifier_model_id = ?, completed_at = ?
        WHERE id = ?
        """,
        (plant_model_id, now, scan_id),
    )
    inconsistent = "inconsistent_plant" in result.reasons
    for prediction in result.image_predictions:
        plant_id = _plant_id(connection, prediction.plant.code)
        if prediction.accepted:
            decision = "accepted"
        elif inconsistent:
            decision = "inconsistent_plant"
        elif "low_confidence" in prediction.reasons:
            decision = "low_confidence"
        else:
            decision = "low_margin"
        _insert_prediction(
            connection,
            scan_image_id=image_ids[prediction.index],
            model_id=plant_model_id,
            plant_id=plant_id,
            plant_code=prediction.plant.code,
            confidence=prediction.plant.confidence,
            margin=prediction.margin,
            accepted=prediction.accepted,
            decision=decision,
            reasons=prediction.reasons,
            now=now,
        )
    connection.execute(
        """
        INSERT INTO manual_confirmations(
            scan_id, suggested_plant_id, action, reason, created_at
        ) VALUES (?, ?, 'requested', ?, ?)
        """,
        (scan_id, suggested_id, _json(result.reasons), now),
    )
    connection.execute(
        """
        INSERT INTO scan_events(scan_id, event_type, event_data, created_at)
        VALUES (?, 'manual_confirmation_requested', ?, ?)
        """,
        (scan_id, _json({"reasons": result.reasons}), now),
    )


def record_analysis(
    images: Sequence[ValidatedImage],
    result: AnalysisResult,
    requested_plant_code: str | None = None,
    *,
    database_path: str | Path | None = None,
    user_id: str | None = None,
    device_id: str | None = None,
) -> str:
    """Persist one successful API outcome without storing image bytes."""

    path = initialize_database(database_path)
    scan_id = str(uuid4())
    now = _now()
    with database_connection(path) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO scan_sessions(
                    id, user_id, device_id, status, image_count,
                    started_at, created_at
                ) VALUES (?, ?, ?, 'processing', ?, ?, ?)
                """,
                (scan_id, user_id, device_id, len(images), now, now),
            )
            image_ids = _insert_images(connection, scan_id, images, now)
            if isinstance(result, AnalyzeResponse):
                _record_completed(
                    connection,
                    scan_id,
                    image_ids,
                    result,
                    requested_plant_code,
                    now,
                )
            else:
                _record_manual_confirmation(
                    connection, scan_id, image_ids, result, now
                )
    return scan_id
