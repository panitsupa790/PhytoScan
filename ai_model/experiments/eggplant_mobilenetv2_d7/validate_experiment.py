from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import tensorflow as tf


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from preprocessing.eggplant import load_config as load_preprocessing_config  # noqa: E402
from training.d7_mobilenetv2 import canonical_json_hash, load_training_config, write_json  # noqa: E402


REQUIRED = {
    "best_head.keras", "best_model.keras", "classification_report.csv",
    "config_snapshot.json", "confusion_matrix.csv", "confusion_matrix.png",
    "confusion_matrix_normalized.csv", "confusion_matrix_normalized.png",
    "history.csv", "history.json", "image_access_audit.json", "metrics.json",
    "model_summary.txt", "run_metadata.json", "training_curves.png",
}


def main() -> int:
    root = Path(__file__).resolve().parent
    config = load_training_config()
    preprocessing_config = load_preprocessing_config()
    errors: list[str] = []
    checked: dict[str, object] = {}
    parameter_counts = None
    for variant in config["preprocessing"]["variants"]:
        run_dir = root / "runs" / variant
        missing = sorted(name for name in REQUIRED if not (run_dir / name).is_file())
        if missing:
            errors.append(f"{variant}: missing {', '.join(missing)}")
            continue
        snapshot = json.loads((run_dir / "config_snapshot.json").read_text(encoding="utf-8"))
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        audit = json.loads((run_dir / "image_access_audit.json").read_text(encoding="utf-8"))
        history = json.loads((run_dir / "history.json").read_text(encoding="utf-8"))
        if snapshot != config:
            errors.append(f"{variant}: config snapshot mismatch")
        if metadata["training_config_sha256"] != canonical_json_hash(config):
            errors.append(f"{variant}: training config hash mismatch")
        if metadata["preprocessing_config_sha256"] != canonical_json_hash(preprocessing_config):
            errors.append(f"{variant}: preprocessing config hash mismatch")
        if metrics["smoke_test"] or metadata["smoke_test"]:
            errors.append(f"{variant}: smoke output found in full runs")
        if audit["unique_paths_accessed"] != config["data"]["expected_counts"]:
            errors.append(f"{variant}: image access counts mismatch")
        if audit["test_image_bytes_accessed"] != 0 or metadata["test_image_bytes_accessed"] != 0:
            errors.append(f"{variant}: test image bytes were accessed")
        if not (1 <= metrics["best_epoch"] <= metrics["epochs_ran"] <= config["training"]["max_epochs"]):
            errors.append(f"{variant}: invalid epoch record")
        if len(history["loss"]) != metrics["epochs_ran"]:
            errors.append(f"{variant}: history length mismatch")
        with (run_dir / "confusion_matrix.csv").open("r", encoding="utf-8", newline="") as csv_file:
            confusion_total = sum(int(row[name]) for row in csv.DictReader(csv_file) for name in config["classes"])
        if confusion_total != config["data"]["expected_counts"]["val"]:
            errors.append(f"{variant}: confusion matrix total mismatch")
        model = tf.keras.models.load_model(run_dir / "best_model.keras", compile=False)
        if model.input_shape != (None, 224, 224, 3) or model.output_shape != (None, 3):
            errors.append(f"{variant}: saved model shape mismatch")
        if parameter_counts is None:
            parameter_counts = metadata["parameter_counts"]
        elif metadata["parameter_counts"] != parameter_counts:
            errors.append(f"{variant}: model parameter counts differ")
        checked[variant] = {
            "validation_macro_f1": metrics["validation_macro_f1"],
            "epochs_ran": metrics["epochs_ran"],
            "best_epoch": metrics["best_epoch"],
            "test_image_bytes_accessed": audit["test_image_bytes_accessed"],
            "saved_model_loadable": True,
        }
    comparison_path = root / "comparison" / "preprocessing_comparison.csv"
    if not comparison_path.is_file():
        errors.append("Missing preprocessing comparison CSV")
    else:
        with comparison_path.open("r", encoding="utf-8", newline="") as csv_file:
            if len(list(csv.DictReader(csv_file))) != 4:
                errors.append("Comparison must contain four full runs")
    result = {
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "variants_checked": checked,
        "parameter_counts": parameter_counts,
        "test_image_bytes_accessed": 0 if not any("test image" in error for error in errors) else None,
    }
    write_json(root / "validation_summary.json", result)
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
