from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.db.database import database_connection


def _summary(row: Any) -> dict[str, Any]:
    content = json.loads(row["content_json"])
    return {
        "plant_code": row["plant_code"],
        "name_th": row["name_th"],
        "name_en": row["name_en"],
        "scientific_name": row["scientific_name"],
        "summary_th": row["summary_th"],
        "cover_image": row["cover_image"],
        "cover_alt_text_th": content["media"]["cover_alt_text_th"],
        "supported_disease_count": len(content["supported_disease_codes"]),
        "review_status": row["review_status"],
    }


def list_plant_library(
    database_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    with database_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT p.code AS plant_code, p.name_th, p.name_en,
                   ple.scientific_name, ple.summary_th, ple.cover_image,
                   ple.review_status, ple.content_json
            FROM plant_library_entries ple
            JOIN plants p ON p.id = ple.plant_id
            WHERE p.is_active = 1
            ORDER BY p.display_order
            """
        ).fetchall()
        return [_summary(row) for row in rows]


def get_plant_library_entry(
    plant_code: str,
    database_path: str | Path | None = None,
) -> dict[str, Any] | None:
    with database_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT ple.content_json
            FROM plant_library_entries ple
            JOIN plants p ON p.id = ple.plant_id
            WHERE p.code = ? AND p.is_active = 1
            """,
            (plant_code.strip().lower(),),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["content_json"])
