from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image


AI_MODEL_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = AI_MODEL_ROOT.parent
if str(AI_MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_ROOT))

from preprocessing.eggplant import VARIANTS, load_config, preprocess_image  # noqa: E402
from generate_previews import (  # noqa: E402
    CLASSES,
    PREVIEW_MANIFEST_FIELDS,
    PREVIEW_PURPOSE,
    STATISTICS_FIELDS,
    aggregate_statistics,
    image_statistics,
    read_split_manifest,
    select_preview_samples,
)


class ValidationError(RuntimeError):
    pass


def read_csv(path: Path, required_fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValidationError(f"Missing experiment report: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = sorted(set(required_fields) - set(reader.fieldnames or ()))
        if missing:
            raise ValidationError(f"{path.name} missing columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def validate() -> list[str]:
    errors: list[str] = []
    config = load_config()
    seed = int(config["random_seed"])
    experiment_root = AI_MODEL_ROOT / "experiments" / "eggplant_preprocessing"
    preview_root = experiment_root / "previews"
    manifest_rows = read_csv(
        experiment_root / "preprocessing_manifest.csv", PREVIEW_MANIFEST_FIELDS
    )
    statistics_rows = read_csv(
        experiment_root / "preprocessing_statistics.csv", STATISTICS_FIELDS
    )
    summary_path = experiment_root / "preprocessing_summary.json"
    if not summary_path.is_file():
        raise ValidationError(f"Missing experiment summary: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    split_manifest = read_split_manifest(
        PROJECT_ROOT / "dataset" / "metadata" / "eggplant_split_manifest.csv"
    )
    samples = select_preview_samples(split_manifest, "train", 5, seed)
    expected_manifest = [
        {
            "source_split": source_row["split"],
            "class": source_row["class"],
            "filename": source_row["filename"],
            "variant": variant,
            "config_version": str(config["config_version"]),
            "seed": str(seed),
            "purpose": PREVIEW_PURPOSE,
        }
        for source_row in samples
        for variant in VARIANTS
    ]
    if manifest_rows != expected_manifest:
        errors.append("Preview manifest is not identical to regenerated seed 42 sample")
    if any(row["source_split"] == "test" for row in manifest_rows):
        errors.append("Test-set row found in preview manifest")
    if len({(row["class"], row["filename"]) for row in manifest_rows}) != 15:
        errors.append("Preview manifest does not contain exactly 15 source images")
    combinations = Counter(
        (row["class"], row["filename"], row["variant"]) for row in manifest_rows
    )
    if any(count != 1 for count in combinations.values()) or len(combinations) != 60:
        errors.append("Preview source/variant combinations are not unique and complete")

    expected_statistics: list[dict[str, object]] = []
    split_root = PROJECT_ROOT / "dataset" / "split" / "eggplant"
    for source_row in samples:
        source_path = (
            split_root
            / source_row["split"]
            / source_row["class"]
            / source_row["filename"]
        )
        source_before = source_path.read_bytes()
        for variant in VARIANTS:
            first = preprocess_image(source_path, variant, config)
            second = preprocess_image(source_path, variant, config)
            if first.tobytes() != second.tobytes():
                errors.append(
                    f"Non-deterministic output: {source_row['class']}/{source_row['filename']} {variant}"
                )
            expected_statistics.append(image_statistics(first, source_row, variant))
        if source_path.read_bytes() != source_before:
            errors.append(f"Source image modified: {source_path}")

    normalized_expected_statistics = [
        {field: str(row[field]) for field in STATISTICS_FIELDS}
        for row in expected_statistics
    ]
    if statistics_rows != normalized_expected_statistics:
        errors.append("Statistics report differs from regenerated preprocessing outputs")

    expected_previews = {f"{class_name}_comparison.jpg" for class_name in CLASSES}
    actual_previews = {
        path.name for path in preview_root.iterdir() if path.is_file()
    } if preview_root.is_dir() else set()
    if actual_previews != expected_previews:
        errors.append(
            f"Preview file set mismatch; expected={sorted(expected_previews)} actual={sorted(actual_previews)}"
        )
    for preview_name in sorted(actual_previews):
        try:
            with Image.open(preview_root / preview_name) as image:
                image.verify()
        except Exception as error:
            errors.append(f"Invalid contact sheet {preview_name}: {error}")

    expected_summary_fields = {
        "config_version": config["config_version"],
        "seed": seed,
        "source_split": "train",
        "test_images_used": 0,
        "images_per_class": 5,
        "source_image_count": 15,
        "variant_output_count": 60,
        "class_counts": {class_name: 5 for class_name in CLASSES},
        "variants": list(VARIANTS),
        "statistics_by_variant": aggregate_statistics(expected_statistics),
        "purpose": PREVIEW_PURPOSE,
        "classification_performance_claim": False,
        "winner_selected": False,
    }
    for field, expected in expected_summary_fields.items():
        if summary.get(field) != expected:
            errors.append(f"Experiment summary mismatch: {field}")
    return errors


def main() -> int:
    try:
        errors = validate()
    except (ValidationError, json.JSONDecodeError) as error:
        errors = [str(error)]
    if errors:
        print("D6 experiment validation: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1
    print("D6 experiment validation: PASS")
    print("Variants: P0 P1 P2 P3")
    print("Output: RGB uint8 224x224")
    print("Preview sources: train=15 val=0 test=0")
    print("Manifest rows: 60")
    print("Statistics rows: 60")
    print("Winner selected: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
