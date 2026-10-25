from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = Path(__file__).resolve().parent
COMPARISON_ROOT = EXPERIMENT_ROOT / "comparison"
RUN_PATHS = {
    "R0": ROOT / "ai_model/experiments/eggplant_efficientnetb0_d8_lite/runs/P3",
    "R1": EXPERIMENT_ROOT / "R1_finetune",
    "R2": EXPERIMENT_ROOT / "R2_class_weight",
    "R3": EXPERIMENT_ROOT / "R3_augmentation",
}
TECHNIQUES = {
    "R0": "Frozen baseline",
    "R1": "Fine-tuning",
    "R2": "Fine-tuning + class weights",
    "R3": "Fine-tuning + class weights + mild augmentation",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def history_analysis(run: str, history: dict[str, list[float]], best_epoch: int) -> dict[str, Any]:
    index = best_epoch - 1
    final = len(history["loss"]) - 1
    return {
        "run": run,
        "epochs_ran": len(history["loss"]),
        "best_epoch": best_epoch,
        "best_train_loss": history["loss"][index],
        "best_validation_loss": history["val_loss"][index],
        "best_train_accuracy": history["accuracy"][index],
        "best_validation_accuracy": history["val_accuracy"][index],
        "final_train_loss": history["loss"][final],
        "final_validation_loss": history["val_loss"][final],
        "final_train_accuracy": history["accuracy"][final],
        "final_validation_accuracy": history["val_accuracy"][final],
        "final_accuracy_gap": history["accuracy"][final] - history["val_accuracy"][final],
        "validation_loss_increase_after_best": history["val_loss"][final] - history["val_loss"][index],
    }


def main() -> int:
    COMPARISON_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    analyses = []
    for run, directory in RUN_PATHS.items():
        metrics = read_json(directory / "metrics.json")
        history = read_json(directory / "history.json")
        duration = metrics.get("training_time_seconds", metrics.get("duration_seconds"))
        rows.append(
            {
                "Run": run,
                "Technique": TECHNIQUES[run],
                "Val Accuracy": metrics["validation_accuracy"],
                "Macro Precision": metrics["validation_macro_precision"],
                "Macro Recall": metrics["validation_macro_recall"],
                "Macro F1": metrics["validation_macro_f1"],
                "Weighted F1": metrics["validation_weighted_f1"],
                "Healthy Recall": metrics["per_class"]["healthy"]["recall"],
                "Leaf Spot Recall": metrics["per_class"]["leaf_spot"]["recall"],
                "Leaf Spot F1": metrics["per_class"]["leaf_spot"]["f1"],
                "Mosaic Virus Recall": metrics["per_class"]["mosaic_virus"]["recall"],
                "Best Epoch": metrics["best_epoch"],
                "Training Time": duration,
            }
        )
        analyses.append(history_analysis(run, history, metrics["best_epoch"]))

    fields = list(rows[0])
    with (COMPARISON_ROOT / "d9_refinement_comparison.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    ranked = sorted(rows, key=lambda row: row["Macro F1"], reverse=True)
    tolerance = 0.005
    close_to_best = [row["Run"] for row in ranked if ranked[0]["Macro F1"] - row["Macro F1"] < tolerance]
    summary = {
        "primary_metric": "validation_macro_f1",
        "close_tolerance": tolerance,
        "best_validation_candidate": ranked[0]["Run"],
        "best_macro_f1": ranked[0]["Macro F1"],
        "close_to_best": close_to_best,
        "ranking": [row["Run"] for row in ranked],
        "selection_note": "R2 has the highest Macro F1 and improves leaf_spot recall/F1 without augmentation.",
        "test_metrics_used": False,
    }
    (COMPARISON_ROOT / "comparison_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (COMPARISON_ROOT / "training_behavior.json").write_text(
        json.dumps(analyses, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
