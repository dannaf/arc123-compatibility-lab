from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_holdout as freezer


COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_FILENAME_HOLDOUT_006.json"


class P0035TransferCohortTests(unittest.TestCase):
    def test_p0035_is_disjoint_all_training_filename_only_cohort(self) -> None:
        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        transfer = cohort["frozen_filename_only_training_50_p0035"]
        import_paths = tuple(
            REPOSITORY_ROOT / item["path"]
            for item in transfer["selection_protocol"]["prior_roster_imports"]
        )
        prior_ids, imports = freezer._excluded_task_ids_from_imports(import_paths)
        selected_ids = {
            record["task_id"]
            for records in transfer["tasks"].values()
            for record in records
        }

        self.assertEqual(transfer["task_count"], 50)
        self.assertEqual(
            {benchmark: len(records) for benchmark, records in transfer["tasks"].items()},
            {"arc1": 25, "arc2": 25},
        )
        self.assertEqual(len(selected_ids), 50)
        self.assertTrue(selected_ids.isdisjoint(prior_ids))
        self.assertEqual(len(imports), 14)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in imports))
        self.assertTrue(
            any(
                item["path"].endswith("ARC12_FILENAME_HOLDOUT_005.json")
                for item in imports
            )
        )
        self.assertTrue(
            any(
                item["path"].endswith("ARC12_DEVELOPMENT_COHORT_008.json")
                for item in imports
            )
        )
        self.assertTrue(
            all(
                record["split"] == "training"
                and len(record["selection_hash"]) == 64
                and len(record["source_sha256"]) == 64
                for records in transfer["tasks"].values()
                for record in records
            )
        )
        self.assertEqual(
            transfer["selection_protocol"]["selection_metadata"]["arc1"]["split_allocation"],
            {"training": 25},
        )
        self.assertEqual(
            transfer["selection_protocol"]["selection_metadata"]["arc2"]["split_allocation"],
            {"training": 25},
        )
        self.assertTrue(all(value is False for value in cohort["live_controller_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
