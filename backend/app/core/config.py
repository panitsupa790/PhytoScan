import os
from dataclasses import dataclass


def _cors_origins_from_env() -> tuple[str, ...]:
    raw_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080,"
        "http://127.0.0.1:3000,http://127.0.0.1:8080",
    )
    return tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())


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
    # Kept only so the previous Eggplant research tests/artifacts remain usable.
    eggplant_model_manifest: str = os.getenv(
        "EGGPLANT_MODEL_MANIFEST",
        "../ai_model/models/eggplant/v1/model_manifest.json",
    )


settings = Settings()
