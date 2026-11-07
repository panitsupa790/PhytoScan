from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.db.database import BACKEND_ROOT, database_connection


DATA_DIR = BACKEND_ROOT / "app" / "data"


def _load_json(filename: str) -> dict[str, Any]:
    with (DATA_DIR / filename).open(encoding="utf-8") as source:
        return json.load(source)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _is_healthy(code: str, name: str) -> bool:
    normalized = f"{code} {name}".lower()
    return "healthy" in normalized or "helathy" in normalized


def _plant_ids(connection: Any) -> dict[str, int]:
    return {
        row["code"]: int(row["id"])
        for row in connection.execute("SELECT id, code FROM plants")
    }


def _seed_plants(connection: Any, plants_data: dict[str, Any], now: str) -> None:
    for display_order, plant in enumerate(plants_data["plants"], start=1):
        connection.execute(
            """
            INSERT INTO plants(
                code, name_th, name_en, is_active, display_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name_th = excluded.name_th,
                name_en = excluded.name_en,
                is_active = 1,
                display_order = excluded.display_order,
                updated_at = excluded.updated_at
            """,
            (
                plant["code"],
                plant["name_th"],
                plant["name_en"],
                display_order,
                now,
                now,
            ),
        )


def _seed_plant_library(
    connection: Any,
    library_data: dict[str, Any],
    plant_ids: dict[str, int],
    now: str,
) -> None:
    expected_codes = set(plant_ids)
    library_codes = {str(plant["plant_code"]) for plant in library_data["plants"]}
    if library_codes != expected_codes:
        raise ValueError("Plant library entries do not match the active plant catalogue")

    for plant in library_data["plants"]:
        plant_code = str(plant["plant_code"])
        connection.execute(
            """
            INSERT INTO plant_library_entries(
                plant_id, scientific_name, summary_th, cover_image,
                review_status, content_json, source_file, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plant_id) DO UPDATE SET
                scientific_name = excluded.scientific_name,
                summary_th = excluded.summary_th,
                cover_image = excluded.cover_image,
                review_status = excluded.review_status,
                content_json = excluded.content_json,
                source_file = excluded.source_file,
                updated_at = excluded.updated_at
            """,
            (
                plant_ids[plant_code],
                plant["taxonomy"]["scientific_name"],
                plant["overview"]["summary_th"],
                plant["media"]["cover_image"],
                plant["review"]["status"],
                json.dumps(plant, ensure_ascii=False, separators=(",", ":")),
                "app/data/plant_library.json",
                now,
            ),
        )


def _seed_diseases(
    connection: Any,
    diseases_data: dict[str, Any],
    plant_ids: dict[str, int],
    now: str,
) -> None:
    for plant_code, plant_id in plant_ids.items():
        for disease_code, disease in diseases_data.get(plant_code, {}).items():
            name_th = disease.get("name_th", disease.get("disease_name_th", ""))
            name_en = disease.get("name_en", disease.get("disease_name_en", disease_code))
            connection.execute(
                """
                INSERT INTO diseases(
                    plant_id, code, name_th, name_en, is_healthy,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(plant_id, code) DO UPDATE SET
                    name_th = excluded.name_th,
                    name_en = excluded.name_en,
                    is_healthy = excluded.is_healthy,
                    is_active = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    plant_id,
                    disease_code,
                    name_th,
                    name_en,
                    int(_is_healthy(disease_code, name_en)),
                    now,
                    now,
                ),
            )
            disease_id = int(
                connection.execute(
                    "SELECT id FROM diseases WHERE plant_id = ? AND code = ?",
                    (plant_id, disease_code),
                ).fetchone()["id"]
            )
            for source_key, guidance_type in (
                ("symptoms", "symptom"),
                ("care", "care"),
                ("prevention", "prevention"),
            ):
                for sort_order, content in enumerate(disease.get(source_key, [])):
                    connection.execute(
                        """
                        INSERT INTO disease_guidance(
                            disease_id, guidance_type, content_th, sort_order,
                            source_reference, review_status
                        ) VALUES (?, ?, ?, ?, ?, 'pending')
                        ON CONFLICT(disease_id, guidance_type, sort_order)
                        DO UPDATE SET
                            content_th = excluded.content_th,
                            source_reference = excluded.source_reference
                        """,
                        (
                            disease_id,
                            guidance_type,
                            content,
                            sort_order,
                            "app/data/diseases.json",
                        ),
                    )


def _seed_model(
    connection: Any,
    model: dict[str, Any],
    input_contract: dict[str, Any],
    plant_ids: dict[str, int],
    now: str,
    *,
    model_type: str,
    plant_code: str | None,
    operating_scope: str | None,
) -> int:
    input_height, input_width, input_channels = model["input_shape"]
    pixel_min, pixel_max = input_contract["pixel_range"]
    plant_id = plant_ids.get(plant_code) if plant_code else None
    connection.execute(
        """
        INSERT INTO model_artifacts(
            model_type, plant_id, model_version, architecture, file_path,
            sha256, input_width, input_height, input_channels, dtype,
            pixel_min, pixel_max, decoder, resize_method, preprocessing,
            external_normalization, operating_scope, is_active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(model_version) DO UPDATE SET
            model_type = excluded.model_type,
            plant_id = excluded.plant_id,
            architecture = excluded.architecture,
            file_path = excluded.file_path,
            sha256 = excluded.sha256,
            input_width = excluded.input_width,
            input_height = excluded.input_height,
            input_channels = excluded.input_channels,
            dtype = excluded.dtype,
            pixel_min = excluded.pixel_min,
            pixel_max = excluded.pixel_max,
            decoder = excluded.decoder,
            resize_method = excluded.resize_method,
            preprocessing = excluded.preprocessing,
            external_normalization = excluded.external_normalization,
            operating_scope = excluded.operating_scope,
            is_active = 1
        """,
        (
            model_type,
            plant_id,
            model["model_version"],
            model["architecture"],
            model["model_path"],
            model["sha256"],
            input_width,
            input_height,
            input_channels,
            input_contract["dtype"],
            pixel_min,
            pixel_max,
            input_contract["decoder"],
            input_contract["resize_method"],
            model["preprocessing"],
            int(input_contract["external_normalization"]),
            operating_scope,
            now,
        ),
    )
    return int(
        connection.execute(
            "SELECT id FROM model_artifacts WHERE model_version = ?",
            (model["model_version"],),
        ).fetchone()["id"]
    )


def _seed_models(
    connection: Any,
    manifest: dict[str, Any],
    metadata: dict[str, Any],
    plant_ids: dict[str, int],
    now: str,
) -> None:
    input_contract = manifest["input_contract"]
    plant_model = manifest["plant_classifier"]
    plant_model_id = _seed_model(
        connection,
        plant_model,
        input_contract,
        plant_ids,
        now,
        model_type="plant_classifier",
        plant_code=None,
        operating_scope=plant_model.get("operating_scope"),
    )

    for class_index, class_code in enumerate(plant_model["class_order"]):
        connection.execute(
            """
            INSERT INTO model_classes(
                model_id, class_index, class_code, plant_id, disease_id
            ) VALUES (?, ?, ?, ?, NULL)
            ON CONFLICT(model_id, class_index) DO UPDATE SET
                class_code = excluded.class_code,
                plant_id = excluded.plant_id,
                disease_id = NULL
            """,
            (plant_model_id, class_index, class_code, plant_ids[class_code]),
        )

    thresholds = metadata["runtime_thresholds"]
    selection = metadata["selection"]
    connection.execute(
        "UPDATE model_thresholds SET is_active = 0 WHERE model_id = ?",
        (plant_model_id,),
    )
    existing_threshold = connection.execute(
        """
        SELECT id FROM model_thresholds
        WHERE model_id = ? AND min_confidence = ? AND min_margin = ?
        """,
        (
            plant_model_id,
            thresholds["min_confidence"],
            thresholds["min_margin"],
        ),
    ).fetchone()
    threshold_values = (
        json.dumps(
            {
                "priority": [
                    "accepted_errors_zero",
                    "coverage_highest",
                    "min_confidence_lowest",
                    "min_margin_lowest",
                ],
                "minimum_accepted_per_true_class": 1,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        selection.get("manifest_sha256"),
        thresholds.get("selection_data"),
        int(thresholds.get("test_adjustment_performed", False)),
        now,
    )
    if existing_threshold is None:
        connection.execute(
            """
            INSERT INTO model_thresholds(
                model_id, min_confidence, min_margin, selection_criteria,
                validation_manifest_sha256, selection_data,
                test_adjustment_performed, frozen_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                plant_model_id,
                thresholds["min_confidence"],
                thresholds["min_margin"],
                *threshold_values,
            ),
        )
    else:
        connection.execute(
            """
            UPDATE model_thresholds SET
                selection_criteria = ?,
                validation_manifest_sha256 = ?,
                selection_data = ?,
                test_adjustment_performed = ?,
                frozen_at = ?,
                is_active = 1
            WHERE id = ?
            """,
            (*threshold_values, int(existing_threshold["id"])),
        )

    for plant_code, disease_model in manifest["models"].items():
        model_id = _seed_model(
            connection,
            disease_model,
            input_contract,
            plant_ids,
            now,
            model_type="disease_classifier",
            plant_code=plant_code,
            operating_scope=plant_model.get("operating_scope"),
        )
        for class_index, class_code in enumerate(disease_model["class_order"]):
            disease = connection.execute(
                "SELECT id FROM diseases WHERE plant_id = ? AND code = ?",
                (plant_ids[plant_code], class_code),
            ).fetchone()
            if disease is None:
                raise ValueError(
                    f"Disease metadata is missing for {plant_code}/{class_code}"
                )
            connection.execute(
                """
                INSERT INTO model_classes(
                    model_id, class_index, class_code, plant_id, disease_id
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(model_id, class_index) DO UPDATE SET
                    class_code = excluded.class_code,
                    plant_id = excluded.plant_id,
                    disease_id = excluded.disease_id
                """,
                (
                    model_id,
                    class_index,
                    class_code,
                    plant_ids[plant_code],
                    int(disease["id"]),
                ),
            )

    for model_id in (
        int(row["id"])
        for row in connection.execute(
            "SELECT id FROM model_artifacts WHERE is_active = 1"
        )
    ):
        existing = connection.execute(
            """
            SELECT id FROM model_deployments
            WHERE model_id = ? AND environment = 'production' AND status = 'active'
            """,
            (model_id,),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO model_deployments(
                    model_id, environment, status, deployed_at, notes
                ) VALUES (?, 'production', 'active', ?, ?)
                """,
                (model_id, now, "Seeded from app/data/model_manifest.json"),
            )


def seed_reference_data(database_path: str | Path | None = None) -> None:
    plants_data = _load_json("plants.json")
    plant_library_data = _load_json("plant_library.json")
    diseases_data = _load_json("diseases.json")
    manifest = _load_json("model_manifest.json")
    metadata = _load_json("plant_classifier_final_metadata.json")
    now = _now()
    with database_connection(database_path) as connection:
        with connection:
            _seed_plants(connection, plants_data, now)
            plant_ids = _plant_ids(connection)
            _seed_plant_library(connection, plant_library_data, plant_ids, now)
            _seed_diseases(connection, diseases_data, plant_ids, now)
            _seed_models(connection, manifest, metadata, plant_ids, now)
