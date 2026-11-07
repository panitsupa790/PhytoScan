from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


MODEL_ORDER = ("v1", "v2", "v3", "v4", "v5", "run08")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize comparable standalone plant-classifier evaluations"
    )
    parser.add_argument("--evaluations-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selected-model", choices=MODEL_ORDER, required=True)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite output directory: {args.output}")

    receipts = {
        name: read_json(args.evaluations_root / name / "evaluation.json")
        for name in MODEL_ORDER
    }
    manifest_hashes = {receipt["manifest"]["sha256"] for receipt in receipts.values()}
    class_orders = {tuple(receipt["class_order"]) for receipt in receipts.values()}
    preprocessing = {
        json.dumps(receipt["preprocessing_contract"], sort_keys=True)
        for receipt in receipts.values()
    }
    dataset_roles = {receipt["dataset_role"] for receipt in receipts.values()}
    if not (
        len(manifest_hashes) == len(class_orders) == len(preprocessing) == len(dataset_roles) == 1
    ):
        raise SystemExit("Evaluations are not directly comparable")

    comparison: list[dict[str, Any]] = []
    high_confidence_errors: list[dict[str, Any]] = []
    for name in MODEL_ORDER:
        receipt = receipts[name]
        metrics = receipt["metrics"]
        predictions = read_rows(args.evaluations_root / name / "row_predictions.csv")
        wrong = [row for row in predictions if row["correct"].lower() != "true"]
        comparison.append(
            {
                "model": name,
                "sha256": receipt["model"]["sha256"],
                "samples": metrics["samples"],
                "correct": metrics["correct"],
                "errors": metrics["samples"] - metrics["correct"],
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
                "macro_recall": metrics["macro_recall"],
                "minimum_per_class_recall": min(metrics["per_class_recall"].values()),
                **{
                    f"recall_{plant}": value
                    for plant, value in metrics["per_class_recall"].items()
                },
                "wrong_confidence_ge_0_90": sum(
                    float(row["top1_confidence"]) >= 0.9 for row in wrong
                ),
            }
        )
        for row in wrong:
            if float(row["top1_confidence"]) >= 0.8:
                high_confidence_errors.append({"model": name, **row})

    args.output.mkdir(parents=True)
    comparison_columns = list(comparison[0])
    with (args.output / "comparison.csv").open(
        "w", encoding="utf-8", newline=""
    ) as target:
        writer = csv.DictWriter(target, fieldnames=comparison_columns)
        writer.writeheader()
        writer.writerows(comparison)

    if high_confidence_errors:
        error_columns = list(high_confidence_errors[0])
        with (args.output / "high_confidence_errors.csv").open(
            "w", encoding="utf-8", newline=""
        ) as target:
            writer = csv.DictWriter(target, fieldnames=error_columns)
            writer.writeheader()
            writer.writerows(high_confidence_errors)

    selected = next(row for row in comparison if row["model"] == args.selected_model)
    summary = {
        "schema_version": 1,
        "dataset_role": next(iter(dataset_roles)),
        "comparability_checks": {
            "same_manifest_sha256": next(iter(manifest_hashes)),
            "same_class_order": list(next(iter(class_orders))),
            "same_preprocessing_contract": json.loads(next(iter(preprocessing))),
            "passed": True,
        },
        "selection": {
            "model": args.selected_model,
            "metrics": selected,
            "decision": "final_integration_baseline_not_proven_global_best",
        },
        "comparison": comparison,
        "limitations": [
            "The shared validation set is controlled-domain but overused and is not an independent blind test.",
            "The set is class-imbalanced, with rose accounting for 1775 of 2340 images.",
            "Macro-F1 and minimum per-class recall are therefore emphasized over overall accuracy.",
            "No locked test was opened or used for this selection.",
            "These results do not support claims about natural or unsupported/OOD images.",
        ],
    }
    (args.output / "comparison.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
