from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_holdout as freezer


class FilenameHoldoutFreezerTests(unittest.TestCase):
    def test_filename_only_selection_is_deterministic_and_stratified(self) -> None:
        inventory = [
            {
                "benchmark": "arc1",
                "split": split,
                "task_id": task_id,
                "source_path": f"/{split}/{task_id}.json",
            }
            for split in ("evaluation", "training")
            for task_id in ("a", "b", "c", "d")
        ]
        allocation = {"evaluation": 2, "training": 2}

        selected_once = freezer._select_records(inventory, {"a"}, "fixed-salt", allocation)
        selected_twice = freezer._select_records(inventory, {"a"}, "fixed-salt", allocation)

        self.assertEqual(selected_once, selected_twice)
        self.assertEqual(len(selected_once), 4)
        self.assertNotIn("a", {record["task_id"] for record in selected_once})
        self.assertEqual(
            {record["split"] for record in selected_once if record["split"] == "evaluation"},
            {"evaluation"},
        )
        self.assertEqual(
            sum(record["split"] == "evaluation" for record in selected_once), 2
        )
        self.assertEqual(sum(record["split"] == "training" for record in selected_once), 2)
        self.assertEqual(
            [record["selection_hash"] for record in selected_once],
            sorted(record["selection_hash"] for record in selected_once),
        )

    def test_filename_only_selection_rejects_insufficient_eligible_records(self) -> None:
        inventory = [
            {
                "benchmark": "arc1",
                "split": "evaluation",
                "task_id": "only-task",
                "source_path": "/evaluation/only-task.json",
            }
        ]

        with self.assertRaises(ValueError):
            freezer._select_records(
                inventory,
                set(),
                "fixed-salt",
                {"evaluation": 2},
            )


if __name__ == "__main__":
    unittest.main()
