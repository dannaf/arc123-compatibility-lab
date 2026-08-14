from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_holdout as freezer


COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_FILENAME_HOLDOUT_008.json"
COHORT_SHA256 = "f1c38ef9392450af767d6f7bcae35b8b27cd9a6db2496eae7b7056b07b703285"


class P0041TransferCohortTests(unittest.TestCase):
    def test_p0041_is_disjoint_final_all_training_filename_only_cohort(self) -> None:
        self.assertEqual(hashlib.sha256(COHORT_PATH.read_bytes()).hexdigest(), COHORT_SHA256)

        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        transfer = cohort["frozen_filename_only_training_38_p0041"]
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

        self.assertEqual(transfer["task_count"], 38)
        self.assertEqual(
            {benchmark: len(records) for benchmark, records in transfer["tasks"].items()},
            {"arc1": 19, "arc2": 19},
        )
        self.assertEqual(len(selected_ids), 38)
        self.assertTrue(selected_ids.isdisjoint(prior_ids))
        self.assertEqual(len(imports), 18)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in imports))
        self.assertTrue(
            any(
                item["path"].endswith("ARC12_FILENAME_HOLDOUT_007.json")
                for item in imports
            )
        )
        self.assertTrue(
            any(
                item["path"].endswith("ARC12_DEVELOPMENT_COHORT_010.json")
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
            {"training": 19},
        )
        self.assertEqual(
            transfer["selection_protocol"]["selection_metadata"]["arc2"]["split_allocation"],
            {"training": 19},
        )
        self.assertTrue(all(value is False for value in cohort["live_controller_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
