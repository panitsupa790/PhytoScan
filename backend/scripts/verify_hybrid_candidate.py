from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import tensorflow as tf


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
DEFAULT_MANIFEST = APP_ROOT / "data" / "model_manifest.hybrid_candidate.json"
DEFAULT_THRESHOLD = (
    APP_ROOT / "data" / "plant_classifier_threshold.hybrid_candidate.json"
)
DEFAULT_REPORT = (
    BACKEND_ROOT / "evaluation" / "hybrid_candidate_v1" / "bundle_verification.json"
)
ACTIVE_MANIFEST = APP_ROOT / "data" / "model_manifest.json"
PLANTS_PATH = APP_ROOT / "data" / "plants.json"
DISEASES_PATH = APP_ROOT / "data" / "diseases.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nested_layers(model: tf.keras.Model) -> Iterable[tf.keras.layers.Layer]:
    for layer in model.layers:
        yield layer
        if isinstance(layer, tf.keras.Model):
            yield from nested_layers(layer)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resolve_model_path(raw_path: str) -> Path:
    path = (APP_ROOT / raw_path).resolve()
    check(APP_ROOT in path.parents, f"Model path is outside app: {raw_path}")
    return path


def verify_model(
    name: str,
    raw: dict[str, Any],
    expected_classes: list[str],
) -> dict[str, Any]:
    path = resolve_model_path(str(raw["model_path"]))
    check(path.is_file(), f"Missing model: {path}")
    actual_sha = sha256_file(path)
    check(actual_sha == str(raw["sha256"]).lower(), f"SHA-256 mismatch: {name}")
    check(raw["class_order"] == expected_classes, f"Class mapping mismatch: {name}")
    model = tf.keras.models.load_model(path, compile=False)
    expected_input = (None, *tuple(raw["input_shape"]))
    expected_output = (None, len(expected_classes))
    check(tuple(model.input_shape) == expected_input, f"Input shape mismatch: {name}")
    check(tuple(model.output_shape) == expected_output, f"Output shape mismatch: {name}")

    preprocessing = str(raw["preprocessing"])
    rescaling = [
        layer for layer in nested_layers(model) if isinstance(layer, tf.keras.layers.Rescaling)
    ]
    if preprocessing == "mobilenet_v2_embedded_minus1_1_from_0_255":
        check(bool(rescaling), f"Missing embedded MobileNetV2 rescaling: {name}")
        check(
            any(
                np.isclose(float(layer.scale), 1.0 / 127.5)
                and np.isclose(float(layer.offset), -1.0)
                for layer in rescaling
            ),
            f"Incorrect embedded MobileNetV2 rescaling: {name}",
        )
    elif preprocessing == "efficientnet_embedded_rescaling_from_0_255":
        check(raw["architecture"] == "EfficientNetB0", "Invalid EfficientNet contract")
    else:
        raise ValueError(f"Unsupported candidate preprocessing: {preprocessing}")

    sample = np.zeros((1, *tuple(raw["input_shape"])), dtype=np.float32)
    output = np.asarray(model(sample, training=False), dtype=np.float32)
    check(
        output.shape == (1, len(expected_classes)),
        f"Inference output mismatch: {name}",
    )
    check(np.isfinite(output).all(), f"Non-finite inference output: {name}")
    check(np.allclose(output.sum(axis=1), 1.0, atol=1e-5), f"Invalid softmax: {name}")
    return {
        "status": "PASS",
        "path": str(path.relative_to(BACKEND_ROOT)).replace("\\", "/"),
        "sha256": actual_sha,
        "architecture": raw["architecture"],
        "input_shape": list(model.input_shape),
        "output_shape": list(model.output_shape),
        "preprocessing": preprocessing,
        "class_order": expected_classes,
    }


def verify(manifest_path: Path, threshold_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    plants = read_json(PLANTS_PATH)["plants"]
    active_plants = [str(row["code"]) for row in plants]
    diseases = read_json(DISEASES_PATH)
    check(manifest["status"] == "candidate_staging_not_active", "Candidate is active")
    check(manifest["activation_requires_explicit_approval"] is True, "Activation guard missing")
    check("sunflower" not in manifest["models"], "Sunflower is present")
    check(
        manifest["plant_classifier"]["class_order"] == active_plants,
        "Plant classifier mapping differs from active plants",
    )
    check(set(manifest["models"]) == set(active_plants), "Disease model set mismatch")

    model_results = {
        "plant_classifier": verify_model(
            "plant_classifier",
            manifest["plant_classifier"],
            active_plants,
        )
    }
    for plant_code in active_plants:
        expected_classes = list(diseases[plant_code])
        model_results[plant_code] = verify_model(
            plant_code,
            manifest["models"][plant_code],
            expected_classes,
        )

    threshold = read_json(threshold_path)
    check(threshold["status"] == "candidate_frozen_before_test", "Threshold is not frozen")
    check(threshold["activation_status"] == "candidate_staging_not_active", "Threshold activation state is invalid")
    check(threshold["test_evaluation_status"] == "not_run", "Candidate Test must remain unopened")
    check(
        threshold["model"]["sha256"] == manifest["plant_classifier"]["sha256"],
        "Threshold/model SHA mismatch",
    )
    check(
        threshold["model"]["class_order"]
        == manifest["plant_classifier"]["class_order"],
        "Threshold/model class mapping mismatch",
    )
    for artifact in threshold["validation_artifacts"].values():
        artifact_path = BACKEND_ROOT / artifact["path"]
        check(artifact_path.is_file(), f"Missing validation artifact: {artifact_path}")
        check(
            sha256_file(artifact_path) == artifact["sha256"],
            f"Validation artifact SHA mismatch: {artifact_path}",
        )

    active = read_json(ACTIVE_MANIFEST)
    check(
        active["plant_classifier"]["sha256"]
        == "5585bb91835006003e6f052c58465d84fc0d9ac6e37227d842a28d18f3991165",
        "Active plant classifier was changed",
    )
    return {
        "status": "PASS",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_manifest": str(manifest_path.relative_to(BACKEND_ROOT)).replace("\\", "/"),
        "candidate_manifest_sha256": sha256_file(manifest_path),
        "threshold_config": str(threshold_path.relative_to(BACKEND_ROOT)).replace("\\", "/"),
        "threshold_config_sha256": sha256_file(threshold_path),
        "tensorflow": tf.__version__,
        "keras": tf.keras.__version__,
        "active_bundle_unchanged": True,
        "test_data_opened_by_verification": False,
        "models": model_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--threshold", type=Path, default=DEFAULT_THRESHOLD)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = verify(args.manifest.resolve(), args.threshold.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
