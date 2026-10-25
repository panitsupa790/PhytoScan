from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from training.d7_mobilenetv2 import load_training_config, write_json  # noqa: E402


FIELDS = [
    "rank", "variant", "validation_macro_f1", "validation_accuracy",
    "validation_macro_precision", "validation_macro_recall", "validation_weighted_f1",
    "leaf_spot_precision", "leaf_spot_recall", "leaf_spot_f1", "best_epoch", "epochs_ran",
    "within_close_candidate_tolerance",
]


def main() -> int:
    config = load_training_config()
    root = Path(__file__).resolve().parent
    rows = []
    for variant in config["preprocessing"]["variants"]:
        metrics_path = root / "runs" / variant / "metrics.json"
        if not metrics_path.is_file():
            raise RuntimeError(f"Missing completed run: {metrics_path}")
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if metrics.get("smoke_test"):
            raise RuntimeError(f"Smoke result cannot enter comparison: {variant}")
        leaf = metrics["per_class"]["leaf_spot"]
        rows.append({
            "variant": variant,
            "validation_macro_f1": metrics["validation_macro_f1"],
            "validation_accuracy": metrics["validation_accuracy"],
            "validation_macro_precision": metrics["validation_macro_precision"],
            "validation_macro_recall": metrics["validation_macro_recall"],
            "validation_weighted_f1": metrics["validation_weighted_f1"],
            "leaf_spot_precision": leaf["precision"], "leaf_spot_recall": leaf["recall"], "leaf_spot_f1": leaf["f1"],
            "best_epoch": metrics["best_epoch"], "epochs_ran": metrics["epochs_ran"],
        })
    rows.sort(key=lambda row: (-row["validation_macro_f1"], -row["leaf_spot_recall"], row["variant"]))
    top_score = rows[0]["validation_macro_f1"]
    tolerance = config["selection"]["close_candidate_tolerance"]
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
        row["within_close_candidate_tolerance"] = top_score - row["validation_macro_f1"] <= tolerance
    comparison_dir = root / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    with (comparison_dir / "preprocessing_comparison.csv").open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    close_candidates = [row["variant"] for row in rows if row["within_close_candidate_tolerance"]]
    summary = {
        "primary_metric": config["selection"]["primary_metric"],
        "top_candidate": rows[0]["variant"],
        "top_validation_macro_f1": top_score,
        "close_candidate_tolerance": tolerance,
        "close_candidates": close_candidates,
        "winner_declared": len(close_candidates) == 1,
        "selection_scope": "Validation only; test image bytes accessed = 0",
        "rows": rows,
    }
    write_json(comparison_dir / "comparison_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
