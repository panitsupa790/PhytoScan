from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from phyto_fasttrack.core import FastTrackError, configure_reproducibility, load_json, records_from_manifest, write_json
from phyto_fasttrack.evaluation import evaluate_model
from phyto_fasttrack.exploratory import prepare_internal_debug_split, train_exploratory


def main() -> int:
    parser = argparse.ArgumentParser(description="Exploratory-only fresh EfficientNet-B0 training")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        config = load_json(args.config)
        if config.get("experiment_role") != "exploratory_only":
            raise FastTrackError("Config is not explicitly exploratory_only")
        safety = config["safety"]
        if not safety.get("production_preflight_unchanged") or any(
            safety.get(name) for name in ("external_development_20_used", "legacy_test_used", "locked_test_used", "deploy_automatically", "promotion_allowed")
        ):
            raise FastTrackError("Exploratory safety contract is invalid")
        configure_reproducibility(int(config["seed"]))
        run_id = args.run_id or datetime.now(timezone.utc).strftime("exploratory_only_%Y%m%dT%H%M%SZ")
        run_dir = Path(config["output_root"]) / run_id
        if run_dir.exists():
            raise FastTrackError(f"Refusing to overwrite run: {run_dir}")
        run_dir.mkdir(parents=True)
        write_json(run_dir / "config_snapshot.json", config)
        train_records, debug_records, split_receipt = prepare_internal_debug_split(config, run_dir / "split")
        training_receipt = train_exploratory(
            config, train_records, debug_records, split_receipt, run_dir / "training"
        )
        selected_model = Path(training_receipt["checkpoints"]["selected_for_debug_report_only"]["path"])
        debug_evaluation = evaluate_model(
            model_path=selected_model,
            records=debug_records,
            manifest_path=Path(split_receipt["internal_debug_manifest"]["path"]),
            output_dir=run_dir / "internal_debug_evaluation",
            dataset_role="exploratory_internal_debug_not_mobile_evidence",
            batch_size=int(config["evaluation"]["batch_size"]),
            notes=[
                "Internal Debug Validation was split from the audited training pool.",
                "This result is not evidence of mobile/natural-image generalization and cannot promote a model.",
            ],
        )
        known_manifest = Path(config["known_failures_manifest"])
        known_records, _ = records_from_manifest(
            known_manifest,
            {"path_column": "path", "label_column": "plant", "source_column": "source"},
            require_files=True,
        )
        known_evaluation = evaluate_model(
            model_path=selected_model,
            records=known_records,
            manifest_path=known_manifest,
            output_dir=run_dir / "known_failures_diagnostic",
            dataset_role="known_failures_diagnostic_not_for_selection",
            batch_size=int(config["evaluation"]["batch_size"]),
            notes=["Known failures were evaluated after checkpoint selection and did not tune any hyperparameter."],
        )
        summary = {
            "status": "exploratory_only_completed",
            "pipeline_succeeded": True,
            "production_model_changed": False,
            "deployment_performed": False,
            "promotion_allowed": False,
            "internal_debug_metrics": debug_evaluation["metrics"],
            "known_failure_metrics": known_evaluation["metrics"],
            "limitations": [
                "Internal Debug Validation comes from the same audited source pool as training.",
                "It is not an external natural/mobile validation set.",
                "The result cannot establish that this model is better than V5.",
            ],
        }
        write_json(run_dir / "exploratory_summary.json", summary)
        print(f"EXPLORATORY_ONLY_COMPLETED: {run_dir}")
        return 0
    except FastTrackError as exc:
        print(f"EXPLORATORY_STOPPED: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
