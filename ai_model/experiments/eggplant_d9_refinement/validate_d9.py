from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import tensorflow as tf


ROOT = Path(__file__).resolve().parents[3]
AI_MODEL_ROOT = ROOT / "ai_model"
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from training.d9_refinement import calculate_class_weights, load_training_config, sha256_file  # noqa: E402


EXPERIMENT_ROOT = Path(__file__).resolve().parent
RUN_PATHS = {
    "R1": EXPERIMENT_ROOT / "R1_finetune",
    "R2": EXPERIMENT_ROOT / "R2_class_weight",
    "R3": EXPERIMENT_ROOT / "R3_augmentation",
}
REQUIRED = (
    "best_model.keras",
    "classification_report.csv",
    "config_snapshot.json",
    "confusion_matrix.csv",
    "confusion_matrix.png",
    "confusion_matrix_normalized.csv",
    "confusion_matrix_normalized.png",
    "history.csv",
    "history.json",
    "image_access_audit.json",
    "metrics.json",
    "model_summary.txt",
    "run_metadata.json",
    "training_curves.png",
    "fine_tune_policy.json",
    "class_weights.json",
    "augmentation.json",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    config = load_training_config()
    expected_weights = calculate_class_weights(config)
    checks: dict[str, bool] = {}
    hashes = set()
    training_config_hashes = set()
    preprocessing_config_hashes = set()
    parameter_counts = set()
    policies = []
    for run, directory in RUN_PATHS.items():
        checks[f"{run}_artifacts_complete"] = all((directory / name).is_file() for name in REQUIRED)
        metadata = read_json(directory / "run_metadata.json")
        audit = read_json(directory / "image_access_audit.json")
        metrics = read_json(directory / "metrics.json")
        policy = read_json(directory / "fine_tune_policy.json")
        weights = read_json(directory / "class_weights.json")
        augmentation = read_json(directory / "augmentation.json")
        hashes.add(metadata["source_checkpoint_sha256"])
        training_config_hashes.add(metadata["training_config_sha256"])
        preprocessing_config_hashes.add(metadata["preprocessing_config_sha256"])
        parameter_counts.add(json.dumps(metadata["parameter_counts"], sort_keys=True))
        policies.append((policy["window_layer_names"], policy["trainable_weight_layers"]))
        checks[f"{run}_counts"] = metadata["train_samples"] == 2425 and metadata["validation_samples"] == 324
        checks[f"{run}_test_frozen"] = audit["unique_paths_accessed"] == {"train": 2425, "val": 324, "test": 0} and audit["test_image_bytes_accessed"] == 0
        checks[f"{run}_batch_norm_frozen"] = policy["batch_normalization_trainable"] == 0
        checks[f"{run}_metrics_complete"] = all(key in metrics for key in ("validation_macro_f1", "per_class")) and "leaf_spot" in metrics["per_class"]
        checks[f"{run}_class_weights_scope"] = weights["enabled"] == (run in ("R2", "R3"))
        if run in ("R2", "R3"):
            parsed = {int(key): value for key, value in weights["weights_by_index"].items()}
            checks[f"{run}_class_weights_formula"] = all(abs(parsed[index] - expected_weights[index]) < 1e-12 for index in expected_weights)
        checks[f"{run}_augmentation_scope"] = augmentation["enabled"] == (run == "R3") and metadata["validation_augmentation_enabled"] is False
        model = tf.keras.models.load_model(directory / "best_model.keras", compile=False)
        checks[f"{run}_model_output"] = model.output_shape[-1] == 3
        tf.keras.backend.clear_session()

    checkpoint = ROOT / config["source"]["checkpoint"]
    checks["same_r0_checkpoint"] = hashes == {config["source"]["checkpoint_sha256"]} and sha256_file(checkpoint) == config["source"]["checkpoint_sha256"]
    checks["same_training_config"] = len(training_config_hashes) == 1
    checks["same_preprocessing_config"] = len(preprocessing_config_hashes) == 1
    checks["same_parameter_counts"] = len(parameter_counts) == 1
    checks["same_fine_tune_policy"] = len({json.dumps(policy) for policy in policies}) == 1
    checks["p3_locked"] = config["source"]["preprocessing_variant"] == "P3"
    comparison = EXPERIMENT_ROOT / "comparison/d9_refinement_comparison.csv"
    with comparison.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    checks["comparison_complete"] = [row["Run"] for row in rows] == ["R0", "R1", "R2", "R3"]
    source_state = read_json(EXPERIMENT_ROOT / "source_state_verification.json")
    checks["source_data_unchanged"] = source_state["pass"]
    result = {"pass": all(checks.values()), "passed": sum(checks.values()), "failed": sum(not value for value in checks.values()), "checks": checks}
    (EXPERIMENT_ROOT / "validation_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
