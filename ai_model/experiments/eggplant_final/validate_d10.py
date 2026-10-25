from __future__ import annotations

import json
import sys
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from finalization.d10_lock import (  # noqa: E402
    CHECKPOINT_PATH,
    EXPERIMENT_ROOT,
    FINAL_CONFIG_PATH,
    PREPROCESSING_CONFIG_PATH,
    read_json,
    sha256_file,
    verify_model,
)


def main() -> int:
    config = read_json(FINAL_CONFIG_PATH)
    manifest = read_json(EXPERIMENT_ROOT / "final_lock_manifest.json")
    d9_config = read_json(CHECKPOINT_PATH.parent / "config_snapshot.json")
    d9_weights = read_json(CHECKPOINT_PATH.parent / "class_weights.json")
    preprocessing = read_json(PREPROCESSING_CONFIG_PATH)
    access = read_json(EXPERIMENT_ROOT / "d10_access_audit.json")
    source = read_json(EXPERIMENT_ROOT / "source_state_verification.json")
    model = verify_model()
    checks = {
        "r2_selected": config["source_run"] == "D9_R2",
        "checkpoint_loads": model["load_successful"],
        "model_architecture": model["architecture"] == "EfficientNetB0" and model["output_classes"] == 3,
        "final_config_exists": FINAL_CONFIG_PATH.is_file(),
        "config_hash": sha256_file(FINAL_CONFIG_PATH) == manifest["final_config_sha256"],
        "checkpoint_hash": sha256_file(CHECKPOINT_PATH) == manifest["checkpoint_sha256"],
        "p3_locked": config["preprocessing"]["parameters"] == preprocessing["variants"]["P3"]["parameters"],
        "class_mapping": config["class_names"] == d9_config["classes"],
        "fine_tuning_locked": config["fine_tuned_top_layers"] == 20,
        "batch_norm_frozen": model["batch_normalization_trainable"] == 0,
        "class_weights_locked": config["class_weights"] == d9_weights["weights_by_class"],
        "augmentation_off": config["augmentation"] is False,
        "test_frozen": access["test_image_bytes_accessed"] == 0 and config["test_evaluated"] is False,
        "counts_locked": config["dataset_counts"] == {"train": 2425, "val": 324, "test": 485},
        "selection_rationale": (EXPERIMENT_ROOT / "D10_SELECTION.md").is_file(),
        "d11_protocol": (EXPERIMENT_ROOT / "D11_TEST_PROTOCOL.md").is_file(),
        "source_data_unchanged": source["pass"],
    }
    result = {
        "pass": all(checks.values()),
        "passed": sum(checks.values()),
        "failed": sum(not value for value in checks.values()),
        "checks": checks,
    }
    (EXPERIMENT_ROOT / "validation_result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
