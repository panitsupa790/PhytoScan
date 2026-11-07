from __future__ import annotations

import unittest
from pathlib import Path

from phyto_fasttrack.exploratory import PoolRow, _group_map, _union_groups_and_duplicates


def row(index: int, plant: str, group: str, phash: str) -> PoolRow:
    return PoolRow(
        path=Path(f"/tmp/{plant}_{index}.jpg"),
        plant=plant,
        label=0,
        source="test",
        semantic_group=group,
        sha256=f"{index:064x}",
        phash=phash,
    )


class ExploratorySplitTests(unittest.TestCase):
    def test_group_map_canonicalizes_cross_manifest_tree_and_roboflow_identity(self) -> None:
        # The integration-level manifests are covered by the exploratory run;
        # keep the unit test focused on the canonical regex contracts.
        import re

        chrys = re.search(r"Tree(\d+)", "Image0553_Leaf56_Tree28_Bacterial.jpg", re.IGNORECASE)
        roboflow = re.match(
            r"(.+)_jpg\.rf\.[0-9a-f]+$",
            "Money_Plant_Healthy_049_jpg.rf.cbeb43738291f9edf73ae39f90cd8d20",
            re.IGNORECASE,
        )
        self.assertEqual(int(chrys.group(1)), 28)
        self.assertEqual(roboflow.group(1).lower(), "money_plant_healthy_049")

    def test_same_group_is_unioned(self) -> None:
        rows = [
            row(1, "rose", "plant_1", "0000000000000000"),
            row(2, "rose", "plant_1", "ffffffffffffffff"),
        ]
        union, audit, phash_only_indexes = _union_groups_and_duplicates(rows, 4)
        self.assertEqual(union.find(0), union.find(1))
        self.assertEqual(audit["cross_class_near_duplicate_count"], 0)
        self.assertEqual(phash_only_indexes, set())

    def test_cross_class_near_phash_is_reported(self) -> None:
        rows = [
            row(1, "rose", "rose_1", "0000000000000000"),
            row(2, "marigold", "marigold_1", "0000000000000001"),
        ]
        _, audit, phash_only_indexes = _union_groups_and_duplicates(rows, 4)
        self.assertEqual(audit["cross_class_near_duplicate_count"], 1)
        self.assertEqual(phash_only_indexes, set())
        self.assertEqual(audit["cross_class_near_duplicate_examples"][0]["distance"], 1)

    def test_same_class_phash_only_is_quarantined_without_inventing_group(self) -> None:
        rows = [
            row(1, "rose", "rose_1", "0000000000000000"),
            row(2, "rose", "rose_2", "0000000000000001"),
        ]
        union, audit, phash_only_indexes = _union_groups_and_duplicates(rows, 4)
        self.assertNotEqual(union.find(0), union.find(1))
        self.assertEqual(audit["same_class_phash_similarity_only_pairs"], 1)
        self.assertEqual(phash_only_indexes, {0, 1})


if __name__ == "__main__":
    unittest.main()
