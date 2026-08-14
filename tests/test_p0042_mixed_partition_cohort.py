from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_holdout as freezer


COHORT_PATH = (
    REPOSITORY_ROOT
    / "research"
    / "cohorts"
    / "ARC12_MIXED_PARTITION_DEVELOPMENT_011.json"
)
COHORT_SHA256 = "a92db58cc84ef10d0cb015dfb0d201a61adf18bf2a24370ba5436bc88a260226"


class P0042MixedPartitionCohortTests(unittest.TestCase):
    def test_p0042_is_disjoint_mixed_partition_filename_only_cohort(self) -> None:
        self.assertEqual(hashlib.sha256(COHORT_PATH.read_bytes()).hexdigest(), COHORT_SHA256)

        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        development = cohort["mixed_partition_development_40_p0042"]
        import_paths = tuple(
            REPOSITORY_ROOT / item["path"]
            for item in development["selection_protocol"]["prior_roster_imports"]
        )
        prior_ids, imports = freezer._excluded_task_ids_from_imports(import_paths)
        selected_ids = {
            record["task_id"]
            for records in development["tasks"].values()
            for record in records
        }

        self.assertEqual(development["task_count"], 40)
        self.assertEqual(
            {benchmark: len(records) for benchmark, records in development["tasks"].items()},
            {"arc1": 20, "arc2": 20},
        )
        self.assertEqual(len(selected_ids), 40)
        self.assertTrue(selected_ids.isdisjoint(prior_ids))
        self.assertEqual(len(imports), 19)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in imports))
        self.assertTrue(
            any(
                item["path"].endswith("ARC12_FILENAME_HOLDOUT_008.json")
                for item in imports
            )
        )
        self.assertTrue(
            all(
                record["split"] == "evaluation"
                and len(record["selection_hash"]) == 64
                and len(record["source_sha256"]) == 64
                for record in development["tasks"]["arc1"]
            )
        )
        self.assertTrue(
            all(
                record["split"] == "training"
                and len(record["selection_hash"]) == 64
                and len(record["source_sha256"]) == 64
                for record in development["tasks"]["arc2"]
            )
        )
        self.assertEqual(
            development["selection_protocol"]["selection_metadata"]["arc1"]["split_allocation"],
            {"evaluation": 20},
        )
        self.assertEqual(
            development["selection_protocol"]["selection_metadata"]["arc2"]["split_allocation"],
            {"training": 20},
        )
        self.assertIn("explicitly non-comparable", cohort["claim_boundary"])
        self.assertTrue(all(value is False for value in cohort["live_controller_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
