from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.image_service import ValidatedImage  # noqa: E402
from app.services.model_registry import (  # noqa: E402
    get_classifier_config,
    get_plant_config,
)
from app.services.plant_classifier_service import (  # noqa: E402
    get_plant_classifier_service,
)
from app.services.plant_model_service import get_model_service  # noqa: E402
from app.services.threshold_config import get_plant_thresholds  # noqa: E402


SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validated_image(path: Path) -> ValidatedImage:
    content = path.read_bytes()
    with Image.open(path) as image:
        image_format = str(image.format or "").upper()
        width, height = image.size
        image.verify()
    if image_format not in {"JPEG", "PNG"}:
        raise ValueError(f"Unsupported image format: {path}")
    return ValidatedImage(
        filename=path.name,
        content_type="image/png" if image_format == "PNG" else "image/jpeg",
        image_format=image_format,
        size_bytes=len(content),
        width=width,
        height=height,
        content=content,
    )


def run(profile: str, image_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(
        (
            path
            for path in image_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        ),
        key=lambda path: path.name.casefold(),
    )
    if not paths:
        raise ValueError("No emulator images found")
    classifier_config = get_classifier_config()
    classifier = get_plant_classifier_service()
    thresholds = get_plant_thresholds()
    rows: list[dict[str, Any]] = []
    for index, path in enumerate(paths):
        image = validated_image(path)
        prediction = classifier.predict_many([image])[0]
        accepted = (
            prediction.confidence >= thresholds.min_confidence
            and prediction.margin >= thresholds.min_margin
        )
        disease_prediction = None
        disease_architecture = None
        disease_model_sha256 = None
        if accepted:
            disease_config = get_plant_config(prediction.plant_code)
            disease = get_model_service(prediction.plant_code).predict(image)
            disease_prediction = disease.class_name
            disease_architecture = disease_config.architecture
            disease_model_sha256 = disease_config.sha256
        row: dict[str, Any] = {
            "index": index,
            "filename": path.name,
            "image_sha256": sha256_bytes(image.content),
            "width": image.width,
            "height": image.height,
            "predicted_plant": prediction.plant_code,
            "plant_confidence": prediction.confidence,
            "plant_margin": prediction.margin,
            "accepted": accepted,
            "decision": "completed" if accepted else "manual_confirmation_required",
            "disease_model_architecture": disease_architecture,
            "disease_model_sha256": disease_model_sha256,
            "predicted_disease": disease_prediction,
        }
        for class_name, probability in prediction.probabilities.items():
            row[f"probability_{class_name}"] = probability
        rows.append(row)
        print(f"{profile}: {index + 1}/{len(paths)} {path.name}", flush=True)
    summary = {
        "profile": profile,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Android emulator /sdcard/Download",
        "image_directory": str(image_dir),
        "image_count": len(rows),
        "model_manifest": settings.model_manifest,
        "plant_classifier": {
            "architecture": classifier_config.architecture,
            "model_version": classifier_config.model_version,
            "sha256": classifier_config.sha256,
        },
        "thresholds": {
            "min_confidence": thresholds.min_confidence,
            "min_margin": thresholds.min_margin,
        },
        "decision_counts": dict(Counter(row["decision"] for row in rows)),
        "predicted_plant_counts": dict(
            Counter(row["predicted_plant"] for row in rows)
        ),
        "ground_truth_status": "NOT VERIFIED",
        "unsupported_ood_status": "NOT VERIFIED",
    }
    return rows, summary


def write_outputs(
    output_dir: Path,
    profile: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{profile}_predictions.csv"
    json_path = output_dir / f"{profile}_summary.json"
    if csv_path.exists() or json_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing {profile} results")
    with csv_path.open("x", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, summary = run(args.profile, args.image_dir.resolve())
    write_outputs(args.output_dir.resolve(), args.profile, rows, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
