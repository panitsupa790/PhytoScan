from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tensorflow as tf


ROOT = Path(__file__).resolve().parents[2]
FINAL_CONFIG_PATH = ROOT / "ai_model/configs/eggplant_final_locked.json"
EXPERIMENT_ROOT = ROOT / "ai_model/experiments/eggplant_final"
CHECKPOINT_PATH = ROOT / "ai_model/experiments/eggplant_d9_refinement/R2_class_weight/best_model.keras"
D9_RUN_ROOT = CHECKPOINT_PATH.parent
PREPROCESSING_CONFIG_PATH = ROOT / "ai_model/configs/eggplant_preprocessing.json"
SPLIT_SUMMARY_PATH = ROOT / "dataset/metadata/eggplant_split_summary.json"


class D10LockError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(checkpoint_path: Path = CHECKPOINT_PATH) -> dict[str, Any]:
    if not checkpoint_path.is_file():
        raise D10LockError(f"Candidate checkpoint not found: {checkpoint_path}")
    model = tf.keras.models.load_model(checkpoint_path, compile=False)
    extractor = model.get_layer("frozen_efficientnetb0_features")
    backbone = extractor.get_layer("efficientnetb0")
    head = model.get_layer("classification_head")
    dropout = head.get_layer("dropout")
    dense = head.get_layer("disease_probabilities")
    rescaling = backbone.get_layer("rescaling")
    normalization = backbone.get_layer("normalization")
    batch_norm_layers = [
        layer for layer in backbone.layers if isinstance(layer, tf.keras.layers.BatchNormalization)
    ]
    verification = {
        "load_successful": True,
        "model_name": model.name,
        "architecture": "EfficientNetB0",
        "input_shape": list(model.input_shape[1:]),
        "output_classes": int(model.output_shape[-1]),
        "feature_extractor": extractor.name,
        "backbone": backbone.name,
        "backbone_layer_count": len(backbone.layers),
        "global_average_pooling_present": "global_average_pool" in [layer.name for layer in extractor.layers],
        "dropout_rate": float(dropout.rate),
        "dense_units": int(dense.units),
        "dense_activation": dense.activation.__name__,
        "batch_normalization_total": len(batch_norm_layers),
        "batch_normalization_trainable": sum(layer.trainable for layer in batch_norm_layers),
        "internal_rescaling_scale": float(rescaling.scale),
        "internal_rescaling_offset": float(rescaling.offset),
        "internal_normalization_layer": normalization.name,
        "checkpoint_sha256": sha256_file(checkpoint_path),
    }
    expected = {
        "input_shape": [224, 224, 3],
        "output_classes": 3,
        "global_average_pooling_present": True,
        "dropout_rate": 0.2,
        "dense_units": 3,
        "dense_activation": "softmax",
        "batch_normalization_trainable": 0,
    }
    for key, value in expected.items():
        if verification[key] != value:
            raise D10LockError(f"Model verification failed for {key}: {verification[key]!r}")
    if abs(verification["internal_rescaling_scale"] - (1.0 / 255.0)) > 1e-12:
        raise D10LockError("EfficientNet internal Rescaling(1/255) is not intact")
    return verification


def build_locked_config() -> tuple[dict[str, Any], dict[str, Any]]:
    preprocessing = read_json(PREPROCESSING_CONFIG_PATH)
    run_config = read_json(D9_RUN_ROOT / "config_snapshot.json")
    metadata = read_json(D9_RUN_ROOT / "run_metadata.json")
    metrics = read_json(D9_RUN_ROOT / "metrics.json")
    weights = read_json(D9_RUN_ROOT / "class_weights.json")
    policy = read_json(D9_RUN_ROOT / "fine_tune_policy.json")
    access = read_json(D9_RUN_ROOT / "image_access_audit.json")
    split_summary = read_json(SPLIT_SUMMARY_PATH)
    model = verify_model()

    classes = run_config["classes"]
    if metadata["run"] != "R2" or classes != ["healthy", "leaf_spot", "mosaic_virus"]:
        raise D10LockError("D9 R2 identity or class mapping is not valid")
    if run_config["runs"]["R2"] != {
        "augmentation": False,
        "class_weights": True,
        "directory": "R2_class_weight",
        "technique": "Fine-tuning + class weights",
    }:
        raise D10LockError("D9 R2 treatment differs from the selected candidate")
    if access["test_image_bytes_accessed"] != 0:
        raise D10LockError("D9 R2 access audit is not Test-frozen")
    if split_summary["counts_per_split"] != {"train": 2425, "val": 324, "test": 485}:
        raise D10LockError("Split metadata counts differ from the D10 protocol")

    p3 = preprocessing["variants"]["P3"]
    locked = {
        "lock_version": "1.0",
        "lock_status": "LOCKED_FOR_D11_FINAL_TEST",
        "plant": "eggplant",
        "model": "EfficientNetB0",
        "pretrained_weights": "imagenet",
        "input_size": [224, 224, 3],
        "preprocessing_variant": "P3",
        "preprocessing": {
            "config_path": PREPROCESSING_CONFIG_PATH.relative_to(ROOT).as_posix(),
            "config_sha256": sha256_file(PREPROCESSING_CONFIG_PATH),
            "resize_policy": preprocessing["resize"]["policy"],
            "interpolation": preprocessing["resize"]["interpolation"],
            "pad_color_rgb": preprocessing["resize"]["pad_color_rgb"],
            "color_mode": preprocessing["output"]["color_mode"],
            "output_dtype": preprocessing["output"]["dtype"],
            "output_value_range": preprocessing["output"]["value_range"],
            "method": p3["method"],
            "parameters": p3["parameters"],
        },
        "normalization": {
            "pipeline_input_dtype": "float32",
            "pipeline_input_value_range": [0, 255],
            "keras_preprocess_input_behavior": "identity_in_tensorflow_2_21",
            "model_internal_layers": ["Rescaling(1/255)", "Normalization"],
            "mobilenetv2_preprocess_input": False,
        },
        "class_names": classes,
        "class_mapping": {str(index): name for index, name in enumerate(classes)},
        "head": {
            "pooling": "GlobalAveragePooling2D",
            "dropout": model["dropout_rate"],
            "dense_units": model["dense_units"],
            "activation": model["dense_activation"],
        },
        "dropout": model["dropout_rate"],
        "fine_tuned_top_layers": policy["top_layer_window"],
        "fine_tuned_layer_names": policy["window_layer_names"],
        "trainable_weight_layer_names": policy["trainable_weight_layers"],
        "batchnorm_frozen": policy["batch_normalization_trainable"] == 0,
        "optimizer": run_config["training"]["optimizer"],
        "learning_rate": run_config["training"]["learning_rate"],
        "loss": run_config["training"]["loss"],
        "batch_size": run_config["training"]["batch_size"],
        "class_weights": weights["weights_by_class"],
        "class_weight_formula": weights["formula"],
        "augmentation": False,
        "seed": run_config["seed"],
        "source_run": "D9_R2",
        "source_checkpoint": CHECKPOINT_PATH.relative_to(ROOT).as_posix(),
        "checkpoint_sha256": model["checkpoint_sha256"],
        "validation_evidence": {
            "accuracy": metrics["validation_accuracy"],
            "macro_f1": metrics["validation_macro_f1"],
            "leaf_spot_recall": metrics["per_class"]["leaf_spot"]["recall"],
            "leaf_spot_f1": metrics["per_class"]["leaf_spot"]["f1"],
            "best_epoch": metrics["best_epoch"],
        },
        "dataset_counts": split_summary["counts_per_split"],
        "test_class_counts": {
            name: split_summary["counts_per_class"][name]["test"] for name in classes
        },
        "test_evaluated": False,
        "test_image_bytes_accessed_during_d10": 0,
    }
    return locked, model


def write_lock() -> dict[str, Any]:
    locked, model_verification = build_locked_config()
    FINAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPERIMENT_ROOT.mkdir(parents=True, exist_ok=True)
    FINAL_CONFIG_PATH.write_text(
        json.dumps(locked, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    config_hash = sha256_file(FINAL_CONFIG_PATH)
    manifest = {
        "lock_status": locked["lock_status"],
        "source_run": locked["source_run"],
        "final_config_path": FINAL_CONFIG_PATH.relative_to(ROOT).as_posix(),
        "final_config_sha256": config_hash,
        "checkpoint_path": locked["source_checkpoint"],
        "checkpoint_sha256": locked["checkpoint_sha256"],
        "hash_scope": "exact file bytes",
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_image_bytes_accessed_during_d10": 0,
        "final_test_evaluation_performed": False,
    }
    (EXPERIMENT_ROOT / "final_lock_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (EXPERIMENT_ROOT / "model_verification.json").write_text(
        json.dumps(model_verification, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (EXPERIMENT_ROOT / "d10_access_audit.json").write_text(
        json.dumps(
            {
                "test_image_bytes_accessed": 0,
                "test_images_decoded": 0,
                "test_inference_performed": False,
                "metadata_only_test_counts_read": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest
