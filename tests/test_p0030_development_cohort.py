from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_holdout as freezer


COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_DEVELOPMENT_COHORT_007.json"


class P0030DevelopmentCohortTests(unittest.TestCase):
    def test_p0030_is_disjoint_metadata_only_development_cohort(self) -> None:
        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        frozen = cohort["development_filename_only_40_p0030"]
        imports = frozen["selection_protocol"]["prior_roster_imports"]
        import_paths = tuple(REPOSITORY_ROOT / item["path"] for item in imports)
        prior_ids, import_metadata = freezer._excluded_task_ids_from_imports(import_paths)
        selected_ids = {
            record["task_id"]
            for records in frozen["tasks"].values()
            for record in records
        }

        self.assertEqual(frozen["task_count"], 40)
        self.assertEqual(
            {benchmark: len(records) for benchmark, records in frozen["tasks"].items()},
            {"arc1": 20, "arc2": 20},
        )
        self.assertEqual(len(selected_ids), 40)
        self.assertTrue(selected_ids.isdisjoint(prior_ids))
        self.assertEqual(len(import_metadata), 11)
        self.assertTrue(
            any(item["path"] == "research/cohorts/ARC12_FILENAME_HOLDOUT_004.json" for item in imports)
        )
        self.assertTrue(all(len(item["sha256"]) == 64 for item in import_metadata))
        for benchmark in ("arc1", "arc2"):
            records = frozen["tasks"][benchmark]
            self.assertEqual(sum(record["split"] == "evaluation" for record in records), 10)
            self.assertEqual(sum(record["split"] == "training" for record in records), 10)
        self.assertTrue(all(value is False for value in cohort["live_controller_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
