from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_development as freezer


class FilenameDevelopmentFreezerTests(unittest.TestCase):
    def test_exclusions_cover_prior_development_and_fresh_holdout(self) -> None:
        task_ids, imports = freezer._excluded_task_ids(freezer.DEFAULT_EXCLUSION_IMPORTS)
        holdout = json.loads(freezer.DEFAULT_EXCLUSION_IMPORTS[1].read_text(encoding="utf-8"))
        holdout_ids = {
            record["task_id"]
            for records in holdout["frozen_filename_only_50"]["tasks"].values()
            for record in records
        }

        self.assertEqual(len(imports), 2)
        self.assertTrue(holdout_ids)
        self.assertTrue(holdout_ids.issubset(task_ids))
        self.assertGreaterEqual(len(task_ids), 160)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in imports))


if __name__ == "__main__":
    unittest.main()
