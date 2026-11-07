from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from natural_dataset_pipeline import (
    CLASS_NAMES,
    _select_components,
    coverage_report,
    import_batch,
    semantic_keys,
    validate_metadata_row,
)


def config() -> dict:
    return {
        "allowed_health_states": ["healthy", "diseased", "insect_damaged", "mixed"],
        "allowed_licenses": ["own_photo", "cc-by-4.0"],
        "minimum_image_side": 32,
        "targets_per_class": {"training": 1, "development": 1, "locked_test": 1},
        "health_targets_per_class": {"healthy": 1, "diseased": 1, "insect_damaged": 1},
    }


def metadata(path: Path, external_id: str = "img-1") -> dict[str, str]:
    return {
        "external_id": external_id,
        "file_path": str(path),
        "plant": "marigold",
        "plant_id": "plant-1",
        "observer_id": "observer-1",
        "session_id": "session-1",
        "source": "mobile",
        "capture_date": "2026-10-30",
        "device": "phone",
        "health_state": "healthy",
        "license": "own_photo",
        "source_url": "N/A",
        "license_url": "N/A",
        "attribution": "owner",
        "natural_background": "yes",
        "notes": "",
    }


class NaturalDatasetPipelineTests(unittest.TestCase):
    def test_metadata_requires_explicit_label_group_license_and_natural_scene(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "leaf.jpg"
            Image.new("RGB", (64, 64), "green").save(image)
            row = metadata(image)
            self.assertEqual(validate_metadata_row(row, config()), [])
            row["plant_id"] = ""
            row["natural_background"] = "no"
            errors = validate_metadata_row(row, config())
            self.assertIn("missing_plant_id", errors)
            self.assertIn("not_declared_natural_background", errors)

    def test_same_observer_key_is_shared_across_classes_and_sessions(self) -> None:
        first = metadata(Path("/tmp/a.jpg"))
        second = dict(first, plant="rose", plant_id="plant-2", session_id="session-2")
        self.assertEqual(semantic_keys(first)[0], semantic_keys(second)[0])
        self.assertNotEqual(semantic_keys(first)[1], semantic_keys(second)[1])

    def test_component_allocator_never_splits_component(self) -> None:
        components = []
        for index, plant in enumerate(CLASS_NAMES):
            components.append(
                {
                    "root": index,
                    "id": f"component-{index}",
                    "indexes": [index, index + 100],
                    "class_counts": {plant: 2},
                }
            )
        roots, counts = _select_components(components, {plant: 1 for plant in CLASS_NAMES}, seed=42)
        self.assertEqual(roots, set(range(6)))
        self.assertTrue(all(counts[plant] == 2 for plant in CLASS_NAMES))

    def test_coverage_requires_health_slices_not_only_total(self) -> None:
        rows = []
        for plant in CLASS_NAMES:
            for index in range(3):
                rows.append(
                    {
                        **metadata(Path("/tmp/a.jpg"), f"{plant}-{index}"),
                        "plant": plant,
                        "health_state": "healthy",
                        "species_confirmed": "yes",
                        "leaf_visible": "yes",
                        "image_quality": "good",
                        "natural_scene_confirmed": "yes",
                        "license_verified": "yes",
                        "review_decision": "approved",
                    }
                )
        report = coverage_report(config(), rows)
        self.assertFalse(report["ready_for_group_split"])
        self.assertEqual(report["classes"]["marigold"]["health_missing"]["diseased"], 1)

    def test_import_is_immutable_and_rejects_reimported_sha(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            (workspace / "imports").mkdir(parents=True)
            image = root / "leaf.jpg"
            Image.new("RGB", (64, 64), "green").save(image)
            metadata_path = root / "metadata.csv"
            row = metadata(image)
            with metadata_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            first = import_batch(config(), workspace, metadata_path, "batch-1")
            self.assertEqual(first["accepted"], 1)
            row["external_id"] = "img-2"
            metadata_path_2 = root / "metadata-2.csv"
            with metadata_path_2.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            second = import_batch(config(), workspace, metadata_path_2, "batch-2")
            self.assertEqual(second["accepted"], 0)
            self.assertEqual(second["rejected"], 1)


if __name__ == "__main__":
    unittest.main()
