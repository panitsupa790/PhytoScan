from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


AI_MODEL_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = (
    AI_MODEL_ROOT
    / "experiments"
    / "eggplant_preprocessing"
    / "generate_previews.py"
)
spec = importlib.util.spec_from_file_location("generate_previews", GENERATOR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load preview generator")
generate_previews = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = generate_previews
spec.loader.exec_module(generate_previews)


PreviewError = generate_previews.PreviewError
select_preview_samples = generate_previews.select_preview_samples


def manifest_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for class_name in ("healthy", "leaf_spot", "mosaic_virus"):
        for split_name in ("train", "val", "test"):
            for index in range(8):
                rows.append(
                    {
                        "class": class_name,
                        "filename": f"{class_name}_{split_name}_{index}.jpg",
                        "sha256": f"{index:064x}",
                        "split": split_name,
                        "seed": "42",
                    }
                )
    return rows


class PreviewSelectionTests(unittest.TestCase):
    def test_selection_is_reproducible_and_stratified(self) -> None:
        rows = manifest_rows()
        first = select_preview_samples(rows, "train", 5, 42)
        repeat = select_preview_samples(rows, "train", 5, 42)

        self.assertEqual(first, repeat)
        self.assertEqual(len(first), 15)
        self.assertTrue(all(row["split"] == "train" for row in first))
        for class_name in ("healthy", "leaf_spot", "mosaic_virus"):
            self.assertEqual(sum(row["class"] == class_name for row in first), 5)

    def test_validation_is_allowed(self) -> None:
        selected = select_preview_samples(manifest_rows(), "val", 1, 42)
        self.assertTrue(all(row["split"] == "val" for row in selected))

    def test_test_split_is_rejected(self) -> None:
        with self.assertRaises(PreviewError):
            select_preview_samples(manifest_rows(), "test", 5, 42)


if __name__ == "__main__":
    unittest.main()
