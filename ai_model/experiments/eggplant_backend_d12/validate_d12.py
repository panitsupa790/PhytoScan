from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
AI_MODEL_ROOT = ROOT / "ai_model"
for path in (BACKEND_ROOT, AI_MODEL_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.api.routes import analyze as analyze_route  # noqa: E402
from app.services.disease_catalog import load_disease_catalog  # noqa: E402
from app.services.eggplant_model_service import (  # noqa: E402
    get_eggplant_model_service,
    preprocess_image,
)


EXPERIMENT_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "ai_model/models/eggplant/v1/model_manifest.json"
LABELS_PATH = ROOT / "ai_model/models/eggplant/v1/labels.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = read_json(MANIFEST_PATH)
    labels = read_json(LABELS_PATH)
    golden = read_json(EXPERIMENT_ROOT / "golden_regression.json")
    performance = read_json(EXPERIMENT_ROOT / "performance_baseline.json")
    http = read_json(EXPERIMENT_ROOT / "http_verification.json")
    immutable = read_json(EXPERIMENT_ROOT / "immutable_state_verification.json")
    config_path = ROOT / manifest["locked_config_path"]
    checkpoint_path = ROOT / manifest["checkpoint_path"]
    service = get_eggplant_model_service()
    model_binaries = [
        path for path in (ROOT / "ai_model/models").rglob("*")
        if path.is_file() and path.suffix.lower() in {".keras", ".h5", ".tflite"}
    ]
    endpoint_results = http["endpoints"]
    checks = {
        "manifest_version": manifest["model_version"] == "eggplant-v1",
        "eggplant_only": manifest["plant"] == "eggplant" and manifest["automatic_plant_classification"] is False,
        "class_mapping": labels == {"0": "healthy", "1": "leaf_spot", "2": "mosaic_virus"} and manifest["class_mapping"] == labels,
        "locked_config_hash": service.manifest["locked_config_sha256"] == manifest["locked_config_sha256"],
        "locked_checkpoint_hash": service.manifest["checkpoint_sha256"] == manifest["checkpoint_sha256"],
        "locked_paths_exist": config_path.is_file() and checkpoint_path.is_file(),
        "model_shape": list(service.model.input_shape[1:]) == [224, 224, 3] and service.model.output_shape[-1] == 3,
        "model_loaded_once": service.load_count == 1 and get_eggplant_model_service() is service,
        "p3_reused": preprocess_image.__module__ == "preprocessing.eggplant" and manifest["preprocessing_variant"] == "P3",
        "mean_probability_aggregation": manifest["multi_image_aggregation"] == "mean_class_probabilities" and golden["three_image_aggregate"]["policy"] == "mean_class_probabilities",
        "golden_validation_only": golden["test_images_used"] == 0 and all(sample["source_split"] == "val" for sample in golden["samples"]),
        "golden_probabilities": all(abs(sum(sample["probabilities"].values()) - 1.0) < 1e-5 for sample in golden["samples"]),
        "disease_metadata_complete": set(load_disease_catalog()["eggplant"]) == {"healthy", "leaf_spot", "mosaic_virus"},
        "mosaic_language": any("ไม่ใช่การยืนยันเชื้อไวรัส" in text for text in load_disease_catalog()["eggplant"]["mosaic_virus"]["symptoms"]),
        "normal_route_real": "mock_ai_service" not in inspect.getsource(analyze_route),
        "http_health_docs": all(endpoint_results[name]["status"] == 200 for name in ("health", "docs", "openapi")),
        "http_one_two_three": all(endpoint_results[name]["status"] == 200 for name in ("analyze_one_image", "analyze_two_images", "analyze_three_images")),
        "http_no_mock_values": http["mock_values_observed"] is False,
        "performance_stable": performance["process_stable"] and http["server"]["process_stable"],
        "no_duplicate_model_binary": not model_binaries,
        "immutable_inputs": immutable["pass"] and all(immutable["checks"].values()),
        "no_training_code": ".fit(" not in inspect.getsource(type(service)),
        "report_exists": (EXPERIMENT_ROOT / "D12_REPORT.md").is_file(),
        "backend_scope_documented": "Automatic plant classification: no" in (BACKEND_ROOT / "README.md").read_text(encoding="utf-8"),
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
