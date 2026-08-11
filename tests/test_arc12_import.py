from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.arc12_import import validate_arc12_cohort_import


class ARC12ImportTests(unittest.TestCase):
    def test_import_preserves_cohort_sizes_and_live_oracle_boundary(self) -> None:
        result = validate_arc12_cohort_import(
            REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_COHORT_IMPORT_001.json"
        )
        self.assertEqual(result["curated_task_count"], 60)
        self.assertEqual(result["frozen_task_count"], 50)
        self.assertEqual(result["live_controller_boundary"], "pass")


if __name__ == "__main__":
    unittest.main()
