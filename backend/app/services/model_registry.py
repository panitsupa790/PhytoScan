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
    decoder: str
    resize_method: str
    sha256: str
    name_th: str
    name_en: str


@dataclass(frozen=True)
class PlantClassifierConfig:
    model_version: str
    model_path: Path
    architecture: str
    input_shape: tuple[int, int, int]
    class_order: tuple[str, ...]
    preprocessing: str
    decoder: str
    resize_method: str
    sha256: str


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _manifest_path() -> Path:
    configured = Path(settings.model_manifest)
    if configured.is_absolute():
        return configured.resolve()
    return (BACKEND_ROOT / configured).resolve()


def _resolve_model_path(raw_path: str, name: str) -> Path:
    model_path = (APP_ROOT / raw_path).resolve()
    if APP_ROOT not in model_path.parents:
        raise ValueError(f"Model path for {name} is outside the application")
    return model_path


def _shape_and_classes(raw: dict[str, Any], name: str) -> tuple[tuple[int, int, int], tuple[str, ...]]:
    shape = tuple(int(value) for value in raw["input_shape"])
    classes = tuple(str(value) for value in raw["class_order"])
    if len(shape) != 3 or not classes or len(classes) != len(set(classes)):
        raise ValueError(f"Invalid model manifest entry for {name}")
    return shape, classes


def _input_contract() -> tuple[str, str]:
    raw = _read_json(_manifest_path())["input_contract"]
    if raw.get("dtype") != "float32" or raw.get("pixel_range") != [0, 255]:
        raise ValueError("Unsupported input dtype or pixel range")
    if raw.get("external_normalization") is not False:
        raise ValueError("Models require normalization embedded in each checkpoint")
    decoder = str(raw["decoder"])
    resize_method = str(raw["resize_method"])
    if decoder != "tensorflow_decode_image_rgb" or resize_method != "tensorflow_bilinear":
        raise ValueError("Unsupported decode/resize contract")
    return decoder, resize_method


@lru_cache(maxsize=1)
def get_classifier_config() -> PlantClassifierConfig:
    manifest = _read_json(_manifest_path())
    raw = manifest["plant_classifier"]
    shape, classes = _shape_and_classes(raw, "plant_classifier")
    decoder, resize_method = _input_contract()
    active_plants = {str(row["code"]) for row in _read_json(PLANTS_PATH)["plants"]}
    if set(classes) != active_plants:
        raise ValueError("Plant classifier classes do not match active plants")
    return PlantClassifierConfig(
        model_version=str(raw["model_version"]),
        model_path=_resolve_model_path(str(raw["model_path"]), "plant_classifier"),
        architecture=str(raw["architecture"]),
        input_shape=shape,
        class_order=classes,
        preprocessing=str(raw["preprocessing"]),
        decoder=decoder,
        resize_method=resize_method,
        sha256=str(raw["sha256"]).lower(),
    )


@lru_cache(maxsize=1)
def get_registry() -> dict[str, PlantModelConfig]:
    plant_rows = _read_json(PLANTS_PATH)["plants"]
    plants = {str(row["code"]): row for row in plant_rows}
    model_rows = _read_json(_manifest_path())["models"]
    registry: dict[str, PlantModelConfig] = {}
    decoder, resize_method = _input_contract()

    for code, raw in model_rows.items():
        if code not in plants or raw["plant_code"] != code:
            raise ValueError(f"Invalid plant metadata for {code}")
        model_path = _resolve_model_path(str(raw["model_path"]), code)
        shape, classes = _shape_and_classes(raw, code)
        registry[code] = PlantModelConfig(
            plant_code=code,
            model_version=str(raw["model_version"]),
            model_path=model_path,
            architecture=str(raw["architecture"]),
            input_shape=shape,
            class_order=classes,
            preprocessing=str(raw["preprocessing"]),
            decoder=decoder,
            resize_method=resize_method,
            sha256=str(raw["sha256"]).lower(),
            name_th=str(plants[code]["name_th"]),
            name_en=str(plants[code]["name_en"]),
        )
    if set(registry) != set(get_classifier_config().class_order):
        raise ValueError("Disease model registry does not match classifier classes")
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
