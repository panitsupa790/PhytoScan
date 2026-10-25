from __future__ import annotations

import unittest

from build_clean_dataset import BuildError
from split_dataset import allocate_counts, generate_assignments, validate_assignments


def validation_rows(class_name: str, count: int) -> list[dict[str, str]]:
    return [
        {
            "class": class_name,
            "filename": f"image_{index:04d}.jpg",
            "sha256": f"{index + {'healthy': 0, 'leaf_spot': 10000, 'mosaic_virus': 20000}[class_name]:064x}",
            "status": "valid",
        }
        for index in range(count)
    ]


class AllocationTests(unittest.TestCase):
    def test_largest_remainder_allocations_match_dataset_counts(self) -> None:
        self.assertEqual(
            allocate_counts(1386), {"train": 1039, "val": 139, "test": 208}
        )
        self.assertEqual(
            allocate_counts(495), {"train": 371, "val": 50, "test": 74}
        )
        self.assertEqual(
            allocate_counts(1353), {"train": 1015, "val": 135, "test": 203}
        )

    def test_allocation_always_accounts_for_every_item(self) -> None:
        for total in range(101):
            self.assertEqual(sum(allocate_counts(total).values()), total)


class AssignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = (
            validation_rows("healthy", 40)
            + validation_rows("leaf_spot", 20)
            + validation_rows("mosaic_virus", 30)
        )

    def test_seed_is_reproducible_and_changes_assignment(self) -> None:
        first = generate_assignments(self.rows, 42)
        repeat = generate_assignments(self.rows, 42)
        changed = generate_assignments(self.rows, 43)

        self.assertEqual(first, repeat)
        self.assertTrue(
            any(
                left["split"] != right["split"]
                for left, right in zip(first, changed)
            )
        )

    def test_assignment_is_stratified_and_unique(self) -> None:
        assignments = generate_assignments(self.rows, 42)
        validate_assignments(assignments, self.rows)

        keys = {(row["class"], row["filename"]) for row in assignments}
        self.assertEqual(len(assignments), len(self.rows))
        self.assertEqual(len(keys), len(self.rows))
        for class_name, total in (("healthy", 40), ("leaf_spot", 20), ("mosaic_virus", 30)):
            expected = allocate_counts(total)
            actual = {
                split_name: sum(
                    row["class"] == class_name and row["split"] == split_name
                    for row in assignments
                )
                for split_name in ("train", "val", "test")
            }
            self.assertEqual(actual, expected)

    def test_sha_leakage_across_splits_is_rejected(self) -> None:
        rows = validation_rows("healthy", 2)
        assignments = [
            {
                "class": "healthy",
                "filename": rows[0]["filename"],
                "sha256": "f" * 64,
                "split": "train",
                "seed": "42",
            },
            {
                "class": "healthy",
                "filename": rows[1]["filename"],
                "sha256": "f" * 64,
                "split": "val",
                "seed": "42",
            },
        ]

        with self.assertRaises(BuildError):
            validate_assignments(assignments, rows)


if __name__ == "__main__":
    unittest.main()
