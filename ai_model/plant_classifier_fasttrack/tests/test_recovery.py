from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from recover_development_validation import (
    _stratified_file_screen,
    filesystem_source_group,
    find_named_plant_directories,
    hamming_distance,
)


class RecoveryTests(unittest.TestCase):
    def test_outermost_same_named_directory_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outer = root / "Rosa"
            inner = outer / "condition" / "Rosa"
            inner.mkdir(parents=True)
            self.assertEqual(find_named_plant_directories(root, "Rosa"), [outer])

    def test_stratified_screen_is_bounded_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = []
            for condition in ("healthy", "disease", "damage"):
                directory = root / condition
                directory.mkdir()
                paths.extend(directory / f"image_{index:03d}.jpg" for index in range(20))
            first = _stratified_file_screen(paths, root, 15)
            second = _stratified_file_screen(paths, root, 15)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 15)
            self.assertEqual({path.parent.name for path in first}, {"healthy", "disease", "damage"})

    def test_phash_distance_uses_all_64_bits(self) -> None:
        self.assertEqual(hamming_distance("0000000000000000", "ffffffffffffffff"), 64)

    def test_semantic_groups_use_tree_or_capture_date(self) -> None:
        tree_source = {"group_regex": r"Tree([0-9]+)", "group_namespace": "chrys_tree"}
        date_source = {"group_regex": r"(?:IMG_)?(20[0-9]{6})", "group_namespace": "rose_date"}
        self.assertEqual(
            filesystem_source_group(tree_source, Path("Healthy/Image0128_Leaf13_Tree07_Healthy.jpg")),
            "chrys_tree::07",
        )
        self.assertEqual(
            filesystem_source_group(date_source, Path("Healthy/no_bg_IMG_20241101_13.jpg")),
            "rose_date::20241101",
        )


if __name__ == "__main__":
    unittest.main()
