from __future__ import annotations

import argparse
from pathlib import Path

from phyto_fasttrack.core import FastTrackError, configure_reproducibility, load_json, records_from_manifest
from phyto_fasttrack.evaluation import evaluate_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a PhytoScan plant checkpoint without notebook state")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-role", required=True)
    parser.add_argument("--path-column")
    parser.add_argument("--label-column")
    parser.add_argument("--source-column")
    parser.add_argument("--split-column")
    parser.add_argument("--split-value")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_json(args.config)
        configure_reproducibility(int(config["seed"]))
        normalized_role = args.dataset_role.strip().lower()
        if normalized_role in {"test", "legacy_test", "locked_test", "legacy-test", "locked-test"}:
            raise FastTrackError(
                "This development evaluator refuses Legacy/Locked Test roles; freeze a separate final-test protocol first"
            )
        settings = {
            "path_column": args.path_column,
            "label_column": args.label_column,
            "source_column": args.source_column,
        }
        if args.split_column:
            settings["split_column"] = args.split_column
        if args.split_value:
            settings["split_value"] = args.split_value
        records, _ = records_from_manifest(args.manifest, settings, require_files=True)
        evaluate_model(
            model_path=args.model,
            records=records,
            manifest_path=args.manifest,
            output_dir=args.output,
            dataset_role=args.dataset_role,
            batch_size=int(config["evaluation"]["batch_size"]),
            notes=["This evaluator never selects or changes a threshold."],
        )
    except FastTrackError as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
