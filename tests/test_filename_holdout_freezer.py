from __future__ import annotations

import json
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

    def test_additional_frozen_rosters_are_excluded_without_grid_access(self) -> None:
        import_paths = (
            REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_COHORT_IMPORT_001.json",
            REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_FILENAME_HOLDOUT_001.json",
            REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_DEVELOPMENT_COHORT_001.json",
            REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_DEVELOPMENT_COHORT_002.json",
            REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_DEVELOPMENT_COHORT_003.json",
            REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_DEVELOPMENT_COHORT_004.json",
        )

        task_ids, imports = freezer._excluded_task_ids_from_imports(import_paths)

        self.assertEqual(len(imports), 6)
        self.assertGreaterEqual(len(task_ids), 320)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in imports))

    def test_p0022_transfer_cohort_is_disjoint_from_every_prior_roster(self) -> None:
        cohort_path = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_FILENAME_HOLDOUT_002.json"
        cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
        frozen = cohort["frozen_filename_only_50_p0022"]
        import_paths = tuple(
            REPOSITORY_ROOT / item["path"]
            for item in frozen["selection_protocol"]["prior_roster_imports"]
        )
        prior_ids, imports = freezer._excluded_task_ids_from_imports(import_paths)
        selected_ids = {
            record["task_id"]
            for records in frozen["tasks"].values()
            for record in records
        }

        self.assertEqual(frozen["task_count"], 50)
        self.assertEqual({benchmark: len(records) for benchmark, records in frozen["tasks"].items()}, {"arc1": 25, "arc2": 25})
        self.assertEqual(len(selected_ids), 50)
        self.assertTrue(selected_ids.isdisjoint(prior_ids))
        self.assertEqual(len(imports), 6)
        self.assertTrue(all(value is False for value in cohort["live_controller_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
