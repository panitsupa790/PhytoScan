from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


APP_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = APP_ROOT.parent
PLANTS_PATH = APP_ROOT / "data" / "plants.json"


class UnsupportedPlantError(ValueError):
    pass


@dataclass(frozen=True)
class PlantModelConfig:
    plant_code: str
    model_version: str
    model_path: Path
    architecture: str
    input_shape: tuple[int, int, int]
    class_order: tuple[str, ...]
    preprocessing: str
    sha256: str
    name_th: str
    name_en: str


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _manifest_path() -> Path:
    configured = Path(settings.model_manifest)
    if configured.is_absolute():
        return configured.resolve()
    return (BACKEND_ROOT / configured).resolve()


@lru_cache(maxsize=1)
def get_registry() -> dict[str, PlantModelConfig]:
    plant_rows = _read_json(PLANTS_PATH)["plants"]
    plants = {str(row["code"]): row for row in plant_rows}
    model_rows = _read_json(_manifest_path())["models"]
    registry: dict[str, PlantModelConfig] = {}

    for code, raw in model_rows.items():
        if code not in plants or raw["plant_code"] != code:
            raise ValueError(f"Invalid plant metadata for {code}")
        model_path = (APP_ROOT / str(raw["model_path"])).resolve()
        if APP_ROOT not in model_path.parents:
            raise ValueError(f"Model path for {code} is outside the application")
        shape = tuple(int(value) for value in raw["input_shape"])
        classes = tuple(str(value) for value in raw["class_order"])
        if len(shape) != 3 or not classes:
            raise ValueError(f"Invalid model manifest entry for {code}")
        registry[code] = PlantModelConfig(
            plant_code=code,
            model_version=str(raw["model_version"]),
            model_path=model_path,
            architecture=str(raw["architecture"]),
            input_shape=shape,
            class_order=classes,
            preprocessing=str(raw["preprocessing"]),
            sha256=str(raw["sha256"]).lower(),
            name_th=str(plants[code]["name_th"]),
            name_en=str(plants[code]["name_en"]),
        )
    return registry


def get_plant_config(plant_code: str) -> PlantModelConfig:
    normalized = plant_code.strip().lower()
    try:
        return get_registry()[normalized]
    except KeyError as error:
        raise UnsupportedPlantError(normalized) from error


def list_supported_plants() -> list[dict[str, str | int]]:
    return [
        {
            "code": config.plant_code,
            "name_th": config.name_th,
            "name_en": config.name_en,
            "disease_count": len(config.class_order),
        }
        for config in get_registry().values()
    ]
