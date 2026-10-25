from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.eggplant_model_service import get_eggplant_model_service  # noqa: E402
from app.services.image_service import ValidatedImage  # noqa: E402


SAMPLES = (
    ("healthy", "Healthy Leaf Image 1001.jpg", "808297e75fe112887169bdadbd3d6a4a21b3ecfff43f4ba5249a9b51ffaa56e4"),
    ("leaf_spot", "Leaf Spot Disease Image 129.jpg", "1b0d65c1e0f9dc2e6019f43fcdf0ca14036704daab0f34b868f21b85f19e7324"),
    ("mosaic_virus", "Mosaic Virus Disease Image 1045.jpg", "fb574f8a89e8412b67719b5b2e60406d401c9b82485bb435b333393bb4859aff"),
)
OUTPUT_PATH = Path(__file__).resolve().parent / "golden_regression.json"
PERFORMANCE_PATH = Path(__file__).resolve().parent / "performance_baseline.json"


def make_image(class_name: str, filename: str, expected_sha256: str) -> ValidatedImage:
    path = ROOT / "dataset/split/eggplant/val" / class_name / filename
    content = path.read_bytes()
    actual_hash = hashlib.sha256(content).hexdigest()
    if actual_hash != expected_sha256:
        raise RuntimeError(f"Validation golden input hash mismatch for {filename}")
    with Image.open(path) as image:
        width, height = image.size
        image_format = str(image.format)
    return ValidatedImage(
        filename=filename,
        content_type="image/jpeg",
        image_format=image_format,
        size_bytes=len(content),
        width=width,
        height=height,
        content=content,
    )


def main() -> int:
    get_eggplant_model_service.cache_clear()
    service = get_eggplant_model_service()
    images = [make_image(*sample) for sample in SAMPLES]
    rows = []
    inference_seconds = []
    for (true_class, filename, input_hash), image in zip(SAMPLES, images):
        processed = service._prepare(image)
        preprocessing_hash = hashlib.sha256(
            processed.astype(np.uint8).tobytes()
        ).hexdigest()
        started = time.perf_counter()
        prediction = service.predict(image)
        inference_seconds.append(time.perf_counter() - started)
        rows.append(
            {
                "source_split": "val",
                "true_class": true_class,
                "filename": filename,
                "input_sha256": input_hash,
                "preprocessing_rgb_uint8_sha256": preprocessing_hash,
                "predicted_class": prediction.class_name,
                "predicted_class_index": prediction.class_index,
                "confidence": prediction.confidence,
                "probabilities": prediction.probabilities,
            }
        )
    started = time.perf_counter()
    aggregate = service.predict_many(images)
    three_image_seconds = time.perf_counter() - started
    golden = {
        "purpose": "D12 development regression; Validation images only",
        "tensorflow_model_version": service.manifest["model_version"],
        "preprocessing_variant": "P3",
        "probability_tolerance": 1e-5,
        "samples": rows,
        "three_image_aggregate": {
            "policy": aggregate.aggregation,
            "predicted_class": aggregate.class_name,
            "confidence": aggregate.confidence,
            "probabilities": aggregate.probabilities,
        },
        "test_images_used": 0,
    }
    performance = {
        "device": "Windows native TensorFlow CPU",
        "model_load_seconds": service.load_seconds,
        "first_single_image_inference_seconds": inference_seconds[0],
        "subsequent_single_image_inference_seconds": inference_seconds[1:],
        "three_image_inference_seconds": three_image_seconds,
        "model_load_count": service.load_count,
        "process_stable": True,
    }
    OUTPUT_PATH.write_text(json.dumps(golden, indent=2) + "\n", encoding="utf-8")
    PERFORMANCE_PATH.write_text(json.dumps(performance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"golden": golden, "performance": performance}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
