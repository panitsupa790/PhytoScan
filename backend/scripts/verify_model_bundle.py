from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BACKEND_ROOT / "app" / "data" / "model_manifest.json"
REPORT_PATH = BACKEND_ROOT / "evaluation" / "model_bundle_verification.json"
REPORT_MARKDOWN_PATH = BACKEND_ROOT / "evaluation" / "model_bundle_verification.md"

SOURCE_LAYOUT = {
    "plant_classifier": ("plant_classifier", "plant-classifier-v1.keras"),
    "chrysanthemum": ("chrysanthemum-v1", "chrysanthemum-v1.keras"),
    "marigold": ("marigold-v1", "marigold-v1.keras"),
    "money_plant": ("money_plant", "money-plant-v1.keras"),
    "rose": ("rose", "rose-v1.keras"),
    "snake_plant": ("snake_plant", "snake-plant-v1.keras"),
    "spider_plant": ("spider_plant", "spider-plant-v1.keras"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def class_order(metadata: dict[str, Any]) -> list[str]:
    values = metadata.get("classes", metadata.get("class_names"))
    if not isinstance(values, list):
        raise ValueError("Missing class order in labels metadata")
    return [str(value) for value in values]


def input_contract(metadata: dict[str, Any]) -> dict[str, Any]:
    raw = metadata.get("input", metadata)
    image_size = raw.get("image_size")
    if image_size is None:
        image_size = [raw.get("height"), raw.get("width")]
    return {
        "image_size": image_size,
        "channels": raw.get("channels", 3),
        "color_mode": raw.get("color_mode"),
        "dtype": raw.get("dtype", "float32"),
        "pixel_range": raw.get("pixel_range"),
        "external_normalization": raw.get("external_normalization", False),
    }


def verify(source_root: Path) -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = {"plant_classifier": manifest["plant_classifier"], **manifest["models"]}
    models = {}
    for name, entry in entries.items():
        source_directory, source_filename = SOURCE_LAYOUT[name]
        source_model = source_root / source_directory / source_filename
        labels_path = source_root / source_directory / "labels.json"
        runtime_model = BACKEND_ROOT / "app" / str(entry["model_path"])
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
        expected_classes = [str(value) for value in entry["class_order"]]
        source_hash = sha256(source_model)
        runtime_hash = sha256(runtime_model)
        recorded_hash = str(entry["sha256"])
        contract = input_contract(labels)
        models[name] = {
            "runtime_path": str(runtime_model),
            "source_path": str(source_model),
            "runtime_size_bytes": runtime_model.stat().st_size,
            "source_size_bytes": source_model.stat().st_size,
            "manifest_sha256": recorded_hash,
            "runtime_sha256": runtime_hash,
            "source_sha256": source_hash,
            "sha256_all_equal": source_hash == runtime_hash == recorded_hash,
            "manifest_class_order": expected_classes,
            "source_class_order": class_order(labels),
            "class_order_equal": class_order(labels) == expected_classes,
            "source_input_contract": contract,
            "input_contract_valid": contract
            == {
                "image_size": [224, 224],
                "channels": 3,
                "color_mode": "RGB",
                "dtype": "float32",
                "pixel_range": [0, 255],
                "external_normalization": False,
            },
        }
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "runtime_models_gitignored": True,
        "required_deployment_action": "Provision all seven .keras files separately and verify SHA-256 before startup.",
        "models": models,
        "all_models_ready": all(
            row["sha256_all_equal"]
            and row["class_order_equal"]
            and row["input_contract_valid"]
            for row in models.values()
        ),
    }


def write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# Model Bundle Verification",
        "",
        f"All seven model artifacts and metadata valid: `{report['all_models_ready']}`.",
        "",
        "| Model | SHA-256 | Class order | Input contract | Runtime bytes |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, row in report["models"].items():
        lines.append(
            f"| {name} | {row['sha256_all_equal']} | {row['class_order_equal']} | "
            f"{row['input_contract_valid']} | {row['runtime_size_bytes']} |"
        )
    lines.extend(
        [
            "",
            "The `.keras` files are intentionally ignored by Git. Deployment must provision all seven files and verify hashes against `model_manifest.json`.",
        ]
    )
    REPORT_MARKDOWN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root", type=Path, default=Path(r"C:\Users\HP\Desktop\PhytoScan")
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify without replacing the existing audit reports.",
    )
    args = parser.parse_args()
    report = verify(args.source_root)
    if not args.check_only:
        write_report(report)
    print(json.dumps({"all_models_ready": report["all_models_ready"]}, indent=2))


if __name__ == "__main__":
    main()
