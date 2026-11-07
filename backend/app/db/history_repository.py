from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.db.database import database_connection


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _owner_clause(
    user_id: str | None, device_id: str | None, *, alias: str = "s."
) -> tuple[str, tuple]:
    if user_id is not None:
        return f"{alias}user_id = ?", (user_id,)
    if device_id is not None:
        return f"{alias}user_id IS NULL AND {alias}device_id = ?", (device_id,)
    return "0 = 1", ()


def _diseases_for_scan(connection: object, scan_id: str) -> list[dict]:
    return [
        {
            "code": row["disease_code_snapshot"],
            "name_th": row["disease_name_th_snapshot"],
            "name_en": row["disease_name_en_snapshot"],
            "confidence": row["confidence"],
        }
        for row in connection.execute(
            """
            SELECT dr.disease_code_snapshot, dr.disease_name_th_snapshot,
                   dr.disease_name_en_snapshot, dr.confidence
            FROM disease_results dr
            JOIN scan_images si ON si.id = dr.scan_image_id
            WHERE si.scan_id = ? AND si.is_deleted = 0
            ORDER BY si.image_index
            """,
            (scan_id,),
        )
    ]


def _summary(connection: object, row: object) -> dict:
    diseases = _diseases_for_scan(connection, row["id"])
    primary = diseases[0] if diseases else {
        "code": "",
        "name_th": "",
        "name_en": "",
        "confidence": None,
    }
    disease_names = []
    for disease in diseases:
        name = disease["name_th"] or disease["name_en"]
        if name and name not in disease_names:
            disease_names.append(name)
    return {
        "id": row["id"],
        "analyzed_at": row["completed_at"] or row["created_at"],
        "plant_code": row["plant_code"],
        "plant_name_th": row["plant_name_th_snapshot"] or row["catalog_name_th"],
        "plant_name_en": row["plant_name_en_snapshot"] or row["catalog_name_en"],
        "plant_confidence": row["plant_confidence"],
        "plant_source": row["plant_source"] or "automatic",
        "image_count": row["image_count"],
        "disease_code": primary["code"],
        "disease_name_th": primary["name_th"],
        "disease_name_en": primary["name_en"],
        "disease_confidence": primary["confidence"],
        "disease_names": disease_names,
        "diseases": diseases,
    }


def list_history(
    *,
    user_id: str | None,
    device_id: str | None,
    limit: int = 50,
    offset: int = 0,
    database_path: str | Path | None = None,
) -> tuple[list[dict], int]:
    owner_sql, owner_params = _owner_clause(user_id, device_id)
    where = f"{owner_sql} AND s.status = 'completed' AND s.deleted_at IS NULL"
    with database_connection(database_path) as connection:
        total = int(
            connection.execute(
                f"SELECT COUNT(*) FROM scan_sessions s WHERE {where}",
                owner_params,
            ).fetchone()[0]
        )
        rows = connection.execute(
            f"""
            SELECT s.*, p.code AS plant_code,
                   p.name_th AS catalog_name_th, p.name_en AS catalog_name_en
            FROM scan_sessions s
            JOIN plants p ON p.id = s.final_plant_id
            WHERE {where}
            ORDER BY COALESCE(s.completed_at, s.created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (*owner_params, limit, offset),
        ).fetchall()
        return [_summary(connection, row) for row in rows], total


def get_history(
    scan_id: str,
    *,
    user_id: str | None,
    device_id: str | None,
    database_path: str | Path | None = None,
) -> dict | None:
    owner_sql, owner_params = _owner_clause(user_id, device_id)
    with database_connection(database_path) as connection:
        row = connection.execute(
            f"""
            SELECT s.*, p.code AS plant_code,
                   p.name_th AS catalog_name_th, p.name_en AS catalog_name_en
            FROM scan_sessions s
            JOIN plants p ON p.id = s.final_plant_id
            WHERE s.id = ? AND {owner_sql} AND s.status = 'completed'
                  AND s.deleted_at IS NULL
            """,
            (scan_id, *owner_params),
        ).fetchone()
        if row is None:
            return None
        result = _summary(connection, row)
        image_rows = connection.execute(
            """
            SELECT si.id, si.image_index, si.original_filename,
                   dr.id AS disease_result_id,
                   dr.disease_code_snapshot, dr.disease_name_th_snapshot,
                   dr.disease_name_en_snapshot, dr.confidence
            FROM scan_images si
            LEFT JOIN disease_results dr ON dr.scan_image_id = si.id
            WHERE si.scan_id = ? AND si.is_deleted = 0
            ORDER BY si.image_index
            """,
            (scan_id,),
        ).fetchall()
        image_results = []
        for image_row in image_rows:
            details = {"symptom": [], "care": [], "prevention": []}
            if image_row["disease_result_id"] is not None:
                for detail in connection.execute(
                    """
                    SELECT detail_type, content FROM result_detail_snapshots
                    WHERE disease_result_id = ? ORDER BY detail_type, sort_order
                    """,
                    (image_row["disease_result_id"],),
                ):
                    details[detail["detail_type"]].append(detail["content"])
            disease = None
            if image_row["disease_result_id"] is not None:
                disease = {
                    "code": image_row["disease_code_snapshot"],
                    "name_th": image_row["disease_name_th_snapshot"],
                    "name_en": image_row["disease_name_en_snapshot"],
                    "confidence": image_row["confidence"],
                }
            image_results.append(
                {
                    "index": image_row["image_index"],
                    "filename": image_row["original_filename"],
                    "disease": disease,
                    "symptoms": details["symptom"],
                    "care": details["care"],
                    "prevention": details["prevention"],
                }
            )
        result["result_agreement"] = (
            None if row["result_agreement"] is None else bool(row["result_agreement"])
        )
        result["image_results"] = image_results
        return result


def delete_history(
    scan_id: str,
    *,
    user_id: str | None,
    device_id: str | None,
    database_path: str | Path | None = None,
) -> int:
    owner_sql, owner_params = _owner_clause(user_id, device_id, alias="")
    with database_connection(database_path) as connection:
        with connection:
            cursor = connection.execute(
                f"""
                UPDATE scan_sessions SET deleted_at = ?
                WHERE id = ? AND {owner_sql} AND deleted_at IS NULL
                """,
                (_now(), scan_id, *owner_params),
            )
            return int(cursor.rowcount)


def clear_history(
    *,
    user_id: str | None,
    device_id: str | None,
    database_path: str | Path | None = None,
) -> int:
    owner_sql, owner_params = _owner_clause(user_id, device_id, alias="")
    with database_connection(database_path) as connection:
        with connection:
            cursor = connection.execute(
                f"""
                UPDATE scan_sessions SET deleted_at = ?
                WHERE {owner_sql} AND deleted_at IS NULL
                """,
                (_now(), *owner_params),
            )
            return int(cursor.rowcount)
