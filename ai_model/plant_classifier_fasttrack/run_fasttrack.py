from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from phyto_fasttrack.core import (
    CLASS_NAMES,
    FastTrackError,
    build_balanced_schedule,
    configure_reproducibility,
    load_json,
    records_from_manifest,
    run_preflight,
    write_csv,
    write_json,
)
from phyto_fasttrack.evaluation import evaluate_model
from phyto_fasttrack.training import evaluate_selected_training_checkpoint, train_fresh_b0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail-closed fresh EfficientNet-B0 training and direct-checkpoint evaluation"
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-id", help="Optional immutable run directory name")
    parser.add_argument("--skip-baseline-diagnostic", action="store_true")
    return parser.parse_args()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("fasttrack_%Y%m%dT%H%M%SZ")


def _comparison_rows(baseline: dict, candidate: dict) -> list[dict[str, object]]:
    baseline_metrics = baseline["metrics"]
    candidate_metrics = candidate["metrics"]
    rows: list[dict[str, object]] = []
    for metric in ("accuracy", "macro_f1", "macro_recall"):
        old = float(baseline_metrics[metric])
        new = float(candidate_metrics[metric])
        rows.append({"metric": metric, "v5": old, "fresh_b0": new, "delta": new - old})
    for class_name in CLASS_NAMES:
        old = float(baseline_metrics["per_class_recall"][class_name])
        new = float(candidate_metrics["per_class_recall"][class_name])
        rows.append(
            {"metric": f"recall_{class_name}", "v5": old, "fresh_b0": new, "delta": new - old}
        )
    return rows


def main() -> int:
    args = parse_args()
    try:
        config = load_json(args.config)
        configure_reproducibility(int(config["seed"]))
        output_root = Path(config["output_root"])
        run_dir = output_root / (args.run_id or _run_id())
        if run_dir.exists():
            raise FastTrackError(f"Refusing to overwrite run directory: {run_dir}")
        run_dir.mkdir(parents=True)
        write_json(run_dir / "config_snapshot.json", config)

        preflight, train_records, development_records = run_preflight(config, require_files=True)
        write_json(run_dir / "preflight.json", preflight)
        _, proposed_sampling = build_balanced_schedule(
            train_records,
            seed=int(config["seed"]),
            max_repeats_per_image=int(config["sampling"]["max_repeats_per_image"]),
        )
        write_json(run_dir / "proposed_sampling_receipt.json", proposed_sampling)
        baseline_result = None
        known_failure_result = None
        baseline_config = config.get("baseline_diagnostic", {})
        if baseline_config.get("enabled", False) and not args.skip_baseline_diagnostic:
            baseline_result = evaluate_model(
                model_path=Path(baseline_config["model_path"]),
                records=development_records,
                manifest_path=Path(config["data"]["development_manifest"]),
                output_dir=run_dir / "v5_overused_development_diagnostic",
                dataset_role="overused_incomplete_development_diagnostic_only",
                batch_size=int(config["evaluation"]["batch_size"]),
                notes=[
                    "This 20-image set is incomplete (no Rose), overused, and cannot support promotion or production claims.",
                    "This diagnostic did not select a model or threshold and did not access Legacy/Locked Test.",
                ],
            )
            known_config = config.get("known_failures", {})
            if known_config.get("manifest"):
                known_manifest = Path(known_config["manifest"])
                known_records, _ = records_from_manifest(known_manifest, known_config, require_files=True)
                known_failure_result = evaluate_model(
                    model_path=Path(baseline_config["model_path"]),
                    records=known_records,
                    manifest_path=known_manifest,
                    output_dir=run_dir / "v5_known_failures",
                    dataset_role="known_failure_regression_diagnostic",
                    batch_size=int(config["evaluation"]["batch_size"]),
                    notes=["Known failures are diagnostic only and do not select a checkpoint."],
                )

        if not preflight["passed"]:
            summary = {
                "status": "blocked_before_training",
                "reason": "Development validation failed the configured quality/completeness gate.",
                "blocking_reasons": preflight["blocking_reasons"],
                "v5_diagnostic_completed": baseline_result is not None,
                "v5_known_failures_completed": known_failure_result is not None,
                "new_model_trained": False,
                "test_accessed": False,
                "deployed": False,
            }
            write_json(run_dir / "run_summary.json", summary)
            print(f"TRAINING_BLOCKED: see {run_dir / 'preflight.json'}")
            return 3

        training_receipt = train_fresh_b0(
            config=config,
            train_records=train_records,
            validation_records=development_records,
            run_dir=run_dir / "fresh_b0_training",
            preflight_report=preflight,
        )
        manifest_path = Path(config["data"]["development_manifest"])
        candidate_result = evaluate_selected_training_checkpoint(
            training_receipt=training_receipt,
            validation_records=development_records,
            manifest_path=manifest_path,
            output_dir=run_dir / "fresh_b0_development_evaluation",
            batch_size=int(config["evaluation"]["batch_size"]),
        )
        known_config = config.get("known_failures", {})
        if known_config.get("manifest"):
            known_manifest = Path(known_config["manifest"])
            known_records, _ = records_from_manifest(known_manifest, known_config, require_files=True)
            evaluate_model(
                model_path=Path(training_receipt["checkpoints"]["selected"]["path"]),
                records=known_records,
                manifest_path=known_manifest,
                output_dir=run_dir / "fresh_b0_known_failures",
                dataset_role="known_failure_regression_diagnostic",
                batch_size=int(config["evaluation"]["batch_size"]),
                notes=["Known failures are diagnostic only and do not select a checkpoint."],
            )
        if baseline_result is None:
            baseline_result = evaluate_model(
                model_path=Path(config["baseline_diagnostic"]["model_path"]),
                records=development_records,
                manifest_path=manifest_path,
                output_dir=run_dir / "v5_development_evaluation",
                dataset_role="eligible_development_validation",
                batch_size=int(config["evaluation"]["batch_size"]),
            )
        comparison = _comparison_rows(baseline_result, candidate_result)
        write_csv(run_dir / "v5_vs_fresh_b0.csv", ["metric", "v5", "fresh_b0", "delta"], comparison)
        macro_delta = next(float(row["delta"]) for row in comparison if row["metric"] == "macro_f1")
        summary = {
            "status": "completed_not_deployed",
            "new_model_trained": True,
            "macro_f1_delta": macro_delta,
            "decision": "retain_candidate_for_review" if macro_delta > 0 else "keep_v5_as_baseline",
            "test_accessed": False,
            "deployed": False,
        }
        write_json(run_dir / "run_summary.json", summary)
        return 0
    except FastTrackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
