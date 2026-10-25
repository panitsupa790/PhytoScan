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
from training.d7_mobilenetv2 import canonical_json_hash, write_json  # noqa: E402
from training.d8_efficientnetb0 import load_training_config  # noqa: E402


REQUIRED = {
    "best_head.keras", "best_model.keras", "classification_report.csv", "config_snapshot.json",
    "confusion_matrix.csv", "confusion_matrix.png", "confusion_matrix_normalized.csv",
    "confusion_matrix_normalized.png", "history.csv", "history.json", "image_access_audit.json",
    "metrics.json", "model_summary.txt", "run_metadata.json", "training_curves.png",
}


def main() -> int:
    root = Path(__file__).resolve().parent
    config = load_training_config()
    preprocessing_config = load_preprocessing_config()
    errors: list[str] = []
    checked = {}
    common_parameters = None
    for variant in ("P0", "P3"):
        run_dir = root / "runs" / variant
        missing = sorted(name for name in REQUIRED if not (run_dir / name).is_file())
        if missing:
            errors.append(f"{variant}: missing {', '.join(missing)}")
            continue
        snapshot = json.loads((run_dir / "config_snapshot.json").read_text(encoding="utf-8"))
        metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        audit = json.loads((run_dir / "image_access_audit.json").read_text(encoding="utf-8"))
        if snapshot != config or metadata["training_config_sha256"] != canonical_json_hash(config):
            errors.append(f"{variant}: training config mismatch")
        if metadata["preprocessing_config_sha256"] != canonical_json_hash(preprocessing_config):
            errors.append(f"{variant}: preprocessing config mismatch")
        if metadata["backbone_frozen"] is not True or metadata["augmentation_enabled"] or metadata["class_balancing_enabled"]:
            errors.append(f"{variant}: controlled policy mismatch")
        if metrics["smoke_test"] or metadata["smoke_test"]:
            errors.append(f"{variant}: smoke result found in full runs")
        if audit["unique_paths_accessed"] != config["data"]["expected_counts"] or audit["test_image_bytes_accessed"] != 0:
            errors.append(f"{variant}: image access audit mismatch")
        with (run_dir / "confusion_matrix.csv").open("r", encoding="utf-8", newline="") as csv_file:
            total = sum(int(row[name]) for row in csv.DictReader(csv_file) for name in config["classes"])
        if total != 324:
            errors.append(f"{variant}: confusion matrix total mismatch")
        model = tf.keras.models.load_model(run_dir / "best_model.keras", compile=False)
        if model.input_shape != (None, 224, 224, 3) or model.output_shape != (None, 3):
            errors.append(f"{variant}: saved model shape mismatch")
        if common_parameters is None:
            common_parameters = metadata["parameter_counts"]
        elif metadata["parameter_counts"] != common_parameters:
            errors.append("P0 and P3 parameter counts differ")
        checked[variant] = {"validation_macro_f1": metrics["validation_macro_f1"], "leaf_spot_recall": metrics["per_class"]["leaf_spot"]["recall"], "best_epoch": metrics["best_epoch"], "test_image_bytes_accessed": 0, "saved_model_loadable": True}
    comparison = root / "comparison" / "model_preprocessing_comparison.csv"
    if not comparison.is_file():
        errors.append("Missing combined comparison")
    result = {"result": "PASS" if not errors else "FAIL", "errors": errors, "variants_checked": checked, "parameter_counts": common_parameters, "test_image_bytes_accessed": 0 if not errors else None}
    write_json(root / "validation_summary.json", result)
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
