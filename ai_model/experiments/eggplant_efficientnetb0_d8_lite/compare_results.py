from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from training.d7_mobilenetv2 import write_json  # noqa: E402
from training.d8_efficientnetb0 import load_training_config  # noqa: E402


FIELDS = ["model", "preprocess", "validation_accuracy", "validation_macro_f1", "leaf_spot_recall", "best_epoch"]


def main() -> int:
    config = load_training_config()
    root = Path(__file__).resolve().parent
    project_root = root.parents[2]
    d7_path = project_root / config["d7_reference"]["comparison_csv"]
    with d7_path.open("r", encoding="utf-8", newline="") as csv_file:
        d7_rows = {row["variant"]: row for row in csv.DictReader(csv_file)}
    rows: list[dict[str, object]] = []
    for variant in ("P0", "P3"):
        reference = config["d7_reference"][variant]
        d7 = d7_rows[variant]
        if abs(float(d7["validation_macro_f1"]) - reference["validation_macro_f1"]) > 1e-12:
            raise RuntimeError(f"D7 {variant} reference does not match its comparison artifact")
        rows.append({
            "model": "MobileNetV2", "preprocess": variant,
            "validation_accuracy": float(d7["validation_accuracy"]),
            "validation_macro_f1": float(d7["validation_macro_f1"]),
            "leaf_spot_recall": float(d7["leaf_spot_recall"]),
            "best_epoch": int(d7["best_epoch"]),
        })
    efficientnet_metrics = {}
    for variant in ("P0", "P3"):
        metrics_path = root / "runs" / variant / "metrics.json"
        if not metrics_path.is_file():
            raise RuntimeError(f"Missing D8 Lite run: {metrics_path}")
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if metrics["smoke_test"]:
            raise RuntimeError("Smoke metrics cannot enter the D8 Lite comparison")
        efficientnet_metrics[variant] = metrics
        rows.append({
            "model": "EfficientNet-B0", "preprocess": variant,
            "validation_accuracy": metrics["validation_accuracy"],
            "validation_macro_f1": metrics["validation_macro_f1"],
            "leaf_spot_recall": metrics["per_class"]["leaf_spot"]["recall"],
            "best_epoch": metrics["best_epoch"],
        })
    comparison_dir = root / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    with (comparison_dir / "model_preprocessing_comparison.csv").open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    p0 = efficientnet_metrics["P0"]
    p3 = efficientnet_metrics["P3"]
    macro_delta = abs(p3["validation_macro_f1"] - p0["validation_macro_f1"])
    p3_lower_leaf_recall = p3["per_class"]["leaf_spot"]["recall"] < p0["per_class"]["leaf_spot"]["recall"]
    reasons = []
    if macro_delta < config["selection"]["tie_breaker_threshold"]:
        reasons.append("EfficientNet P0/P3 macro F1 difference is below 0.005")
    if p3_lower_leaf_recall:
        reasons.append("EfficientNet P3 leaf_spot recall is below P0")
    top = max(rows, key=lambda row: (row["validation_macro_f1"], row["leaf_spot_recall"]))
    summary = {
        "efficientnet_p3_minus_p0_macro_f1": p3["validation_macro_f1"] - p0["validation_macro_f1"],
        "efficientnet_p3_minus_p0_leaf_spot_recall": p3["per_class"]["leaf_spot"]["recall"] - p0["per_class"]["leaf_spot"]["recall"],
        "p2_tie_breaker_recommended": bool(reasons),
        "p2_tie_breaker_reasons": reasons,
        "validation_top_candidate": {"model": top["model"], "preprocess": top["preprocess"], "validation_macro_f1": top["validation_macro_f1"]},
        "selection_scope": "Validation only; no final model decision and test image bytes accessed = 0",
        "rows": rows,
    }
    write_json(comparison_dir / "comparison_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
