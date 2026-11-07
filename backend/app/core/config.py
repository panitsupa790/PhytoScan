import os
from dataclasses import dataclass


def _cors_origins_from_env() -> tuple[str, ...]:
    raw_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080,"
        "http://127.0.0.1:3000,http://127.0.0.1:8080",
    )
    return tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())


def _bool_from_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


@dataclass(frozen=True)
class Settings:
    app_name: str = "PhytoScan API"
    api_v1_prefix: str = "/api/v1"
    max_images: int = int(os.getenv("MAX_IMAGES", "3"))
    max_image_size_bytes: int = int(
        os.getenv("MAX_IMAGE_SIZE_BYTES", str(10 * 1024 * 1024))
    )
    cors_origins: tuple[str, ...] = _cors_origins_from_env()
    model_manifest: str = os.getenv(
        "MODEL_MANIFEST",
        "app/data/model_manifest.json",
    )
    plant_threshold_config: str = os.getenv(
        "PLANT_THRESHOLD_CONFIG",
        "app/data/plant_classifier_evaluation_corrective.json",
    )
    plant_threshold_receipt: str = os.getenv(
        "PLANT_THRESHOLD_RECEIPT",
        "app/data/plant_classifier_corrective_test_receipt.json",
    )
    plant_threshold_require_test_receipt: bool = _bool_from_env(
        "PLANT_THRESHOLD_REQUIRE_TEST_RECEIPT",
        True,
    )
    database_path: str = os.getenv("DATABASE_PATH", "data/phytoscan.db")
    # Kept only so the previous Eggplant research tests/artifacts remain usable.
    eggplant_model_manifest: str = os.getenv(
        "EGGPLANT_MODEL_MANIFEST",
        "../ai_model/models/eggplant/v1/model_manifest.json",
    )


settings = Settings()
