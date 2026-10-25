from __future__ import annotations

import unittest

from build_clean_dataset import BuildError, create_plan, validate_review_value


HASH = "a" * 64


def validation_row(class_name: str, filename: str) -> dict[str, str]:
    return {
        "class": class_name,
        "filename": filename,
        "extension": ".jpg",
        "width": "100",
        "height": "100",
        "mode": "RGB",
        "sha256": HASH,
        "status": "valid",
        "error": "",
    }


def duplicate_row(
    duplicate_type: str, class_name: str, filename: str
) -> dict[str, str]:
    return {
        "sha256": HASH,
        "duplicate_type": duplicate_type,
        "class": class_name,
        "filename": filename,
    }


class ReviewValidationTests(unittest.TestCase):
    def test_unresolved_review_blocks_build(self) -> None:
        with self.assertRaises(BuildError):
            validate_review_value(
                "UNCERTAIN", {"CORRECT", "INCORRECT", "UNCERTAIN"}, "UNCERTAIN", "sample"
            )

    def test_unsupported_review_value_blocks_build(self) -> None:
        with self.assertRaises(BuildError):
            validate_review_value("MAYBE", {"KEEP", "REJECT"}, "", "sample")


class PlanningTests(unittest.TestCase):
    def test_same_class_duplicate_uses_lexical_canonical_file(self) -> None:
        validation = [
            validation_row("healthy", "b.jpg"),
            validation_row("healthy", "a.jpg"),
        ]
        duplicates = [
            duplicate_row("same_class", "healthy", "b.jpg"),
            duplicate_row("same_class", "healthy", "a.jpg"),
        ]

        plan, conflicts = create_plan(validation, duplicates, [], [], [])
        actions = {row["source_filename"]: row["action"] for row in plan}

        self.assertEqual(actions, {"a.jpg": "KEEP", "b.jpg": "DEDUPLICATED"})
        self.assertEqual(conflicts, [])

    def test_random_reject_has_precedence_over_same_class_canonical(self) -> None:
        validation = [
            validation_row("healthy", "a.jpg"),
            validation_row("healthy", "b.jpg"),
        ]
        duplicates = [
            duplicate_row("same_class", "healthy", "a.jpg"),
            duplicate_row("same_class", "healthy", "b.jpg"),
        ]
        audit = [
            {
                "class": "healthy",
                "filename": "a.jpg",
                "review_status": "INCORRECT",
                "reviewer": "reviewer",
                "notes": "",
            }
        ]

        plan, _ = create_plan(validation, duplicates, [], [], audit)
        rows = {row["source_filename"]: row for row in plan}

        self.assertEqual(rows["a.jpg"]["action"], "REJECT")
        self.assertEqual(rows["a.jpg"]["reason"], "RANDOM_AUDIT_INCORRECT")
        self.assertEqual(rows["b.jpg"]["action"], "KEEP")

    def test_cross_class_keep_selects_existing_file_from_target_class(self) -> None:
        validation = [
            validation_row("healthy", "healthy.jpg"),
            validation_row("leaf_spot", "spot.jpg"),
        ]
        duplicates = [
            duplicate_row("cross_class", "healthy", "healthy.jpg"),
            duplicate_row("cross_class", "leaf_spot", "spot.jpg"),
        ]
        cross = [
            {
                "group_id": "group_001",
                "sha256": HASH,
                "class_a": "healthy",
                "filename_a": "healthy.jpg",
                "class_b": "leaf_spot",
                "filename_b": "spot.jpg",
                "decision": "KEEP_LEAF_SPOT",
                "reviewer": "reviewer",
                "notes": "",
            }
        ]

        plan, conflicts = create_plan(validation, duplicates, cross, [], [])
        rows = {(row["source_class"], row["source_filename"]): row for row in plan}

        self.assertEqual(rows[("leaf_spot", "spot.jpg")]["action"], "KEEP")
        self.assertEqual(rows[("leaf_spot", "spot.jpg")]["final_class"], "leaf_spot")
        self.assertEqual(rows[("healthy", "healthy.jpg")]["action"], "DEDUPLICATED")
        self.assertEqual(conflicts, [])

    def test_cross_class_reject_both_rejects_every_member(self) -> None:
        validation = [
            validation_row("healthy", "healthy.jpg"),
            validation_row("leaf_spot", "spot.jpg"),
        ]
        duplicates = [
            duplicate_row("cross_class", "healthy", "healthy.jpg"),
            duplicate_row("cross_class", "leaf_spot", "spot.jpg"),
        ]
        cross = [
            {
                "group_id": "group_001",
                "sha256": HASH,
                "class_a": "healthy",
                "filename_a": "healthy.jpg",
                "class_b": "leaf_spot",
                "filename_b": "spot.jpg",
                "decision": "REJECT_BOTH",
                "reviewer": "reviewer",
                "notes": "",
            }
        ]

        plan, _ = create_plan(validation, duplicates, cross, [], [])

        self.assertTrue(all(row["action"] == "REJECT" for row in plan))
        self.assertTrue(all(row["reason"] == "CROSS_CLASS_REJECT_BOTH" for row in plan))

    def test_quality_reject_overrides_cross_class_keep_and_is_reported(self) -> None:
        validation = [
            validation_row("healthy", "healthy.jpg"),
            validation_row("leaf_spot", "spot.jpg"),
        ]
        duplicates = [
            duplicate_row("cross_class", "healthy", "healthy.jpg"),
            duplicate_row("cross_class", "leaf_spot", "spot.jpg"),
        ]
        cross = [
            {
                "group_id": "group_001",
                "sha256": HASH,
                "class_a": "healthy",
                "filename_a": "healthy.jpg",
                "class_b": "leaf_spot",
                "filename_b": "spot.jpg",
                "decision": "KEEP_LEAF_SPOT",
                "reviewer": "cross reviewer",
                "notes": "",
            }
        ]
        audit = [
            {
                "class": "leaf_spot",
                "filename": "spot.jpg",
                "review_status": "INCORRECT",
                "reviewer": "audit reviewer",
                "notes": "",
            }
        ]

        plan, conflicts = create_plan(validation, duplicates, cross, [], audit)

        self.assertEqual(sum(row["action"] == "KEEP" for row in plan), 0)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["higher_priority_reason"], "RANDOM_AUDIT_INCORRECT")


if __name__ == "__main__":
    unittest.main()
