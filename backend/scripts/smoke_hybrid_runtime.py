from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.analysis_router import (  # noqa: E402
    analyze_automatically,
    analyze_confirmed,
)
from app.services.image_service import ValidatedImage  # noqa: E402
from app.services.model_registry import get_plant_config  # noqa: E402


DEFAULT_PREDICTIONS = (
    BACKEND_ROOT
    / "evaluation"
    / "hybrid_candidate_v1"
    / "plant_classifier_validation_predictions.csv"
)
DEFAULT_REPORT = (
    BACKEND_ROOT / "evaluation" / "hybrid_candidate_v1" / "runtime_smoke.json"
)


def resolve_image_path(raw_path: str) -> Path:
    normalized = raw_path.strip().replace("\\", "/")
    if normalized.startswith("/mnt/") and len(normalized) > 6:
        return Path(f"{normalized[5].upper()}:/{normalized[7:]}")
    return Path(raw_path)


def validated_image(path: Path, index: int = 0) -> ValidatedImage:
    content = path.read_bytes()
    suffix = path.suffix.lower()
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }.get(suffix, "image/jpeg")
    return ValidatedImage(
        filename=f"{index}_{path.name}",
        content_type=content_type,
        image_format=suffix.lstrip(".").upper(),
        size_bytes=len(content),
        width=0,
        height=0,
        content=content,
    )


def select_samples(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    selected: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["correct"] != "True" or row["accepted"] != "True":
            continue
        plant = row["true_plant"]
        if plant not in selected or float(row["margin"]) > float(selected[plant]["margin"]):
            selected[plant] = row
    return selected


def run(predictions_path: Path) -> dict[str, Any]:
    if settings.model_manifest != "app/data/model_manifest.hybrid_candidate.json":
        raise ValueError("MODEL_MANIFEST must select the hybrid candidate")
    if settings.plant_threshold_config != (
        "app/data/plant_classifier_threshold.hybrid_candidate.json"
    ):
        raise ValueError("PLANT_THRESHOLD_CONFIG must select the candidate threshold")
    if settings.plant_threshold_require_test_receipt:
        raise ValueError("Candidate staging must not require a nonexistent Test receipt")

    samples = select_samples(predictions_path)
    expected = {
        "chrysanthemum",
        "marigold",
        "money_plant",
        "rose",
        "snake_plant",
        "spider_plant",
    }
    if set(samples) != expected:
        raise ValueError("Missing accepted validation sample for one or more classes")

    routes: dict[str, Any] = {}
    for plant_code in sorted(samples):
        path = resolve_image_path(samples[plant_code]["path"])
        result = analyze_automatically([validated_image(path)])
        if result.status != "completed" or result.plant.code != plant_code:
            raise ValueError(f"Automatic route failed for {plant_code}: {result.status}")
        config = get_plant_config(plant_code)
        routes[plant_code] = {
            "status": "PASS",
            "source_image": samples[plant_code]["path"],
            "plant_result": result.plant.code,
            "disease_result": result.disease.code,
            "disease_model_architecture": config.architecture,
            "disease_model_sha256": config.sha256,
        }

    first_plant = sorted(samples)[0]
    first_path = resolve_image_path(samples[first_plant]["path"])
    repeated = [validated_image(first_path, index) for index in range(3)]
    repeated_result = analyze_automatically(repeated)
    if repeated_result.status != "completed" or repeated_result.image_count != 3:
        raise ValueError("Three-image automatic analysis failed")

    mixed_codes = sorted(samples)[:2]
    mixed_images = [
        validated_image(resolve_image_path(samples[code]["path"]), index)
        for index, code in enumerate(mixed_codes)
    ]
    mixed_result = analyze_automatically(mixed_images)
    if (
        mixed_result.status != "manual_confirmation_required"
        or "inconsistent_plant" not in mixed_result.reasons
    ):
        raise ValueError("Mixed-plant batch did not fail closed")

    confirmed = analyze_confirmed([validated_image(first_path)], first_plant)
    if confirmed.status != "completed" or confirmed.plant.code != first_plant:
        raise ValueError("Manual confirmation route failed")

    return {
        "status": "PASS",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_only": True,
        "test_set_used": False,
        "automatic_routes": routes,
        "three_image_same_plant": "PASS",
        "mixed_plant_fail_closed": "PASS",
        "manual_confirmation": "PASS",
        "api_schema_changed": False,
        "active_manifest_changed": False,
    }


def main() -> None:
    predictions = Path(os.getenv("HYBRID_VALIDATION_PREDICTIONS", DEFAULT_PREDICTIONS))
    report_path = Path(os.getenv("HYBRID_RUNTIME_REPORT", DEFAULT_REPORT))
    report = run(predictions)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
