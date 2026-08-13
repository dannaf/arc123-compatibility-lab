from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_holdout as standard_freezer
import freeze_arc12_filename_training_holdout as training_freezer


class FilenameTrainingHoldoutFreezerTests(unittest.TestCase):
    def test_wrapper_scopes_training_only_configuration(self) -> None:
        original_allocation = dict(standard_freezer.DEFAULT_ALLOCATION)
        observed: dict[str, object] = {}

        def inspect_configuration() -> int:
            observed["allocation"] = dict(standard_freezer.DEFAULT_ALLOCATION)
            observed["salt"] = standard_freezer.DEFAULT_SALT
            observed["cohort_key"] = standard_freezer.DEFAULT_COHORT_KEY
            return 19

        with mock.patch.object(standard_freezer, "main", side_effect=inspect_configuration):
            self.assertEqual(training_freezer.main(), 19)

        self.assertEqual(observed["allocation"], {"training": 25})
        self.assertEqual(observed["salt"], training_freezer.DEFAULT_SALT)
        self.assertEqual(observed["cohort_key"], training_freezer.DEFAULT_COHORT_KEY)
        self.assertEqual(standard_freezer.DEFAULT_ALLOCATION, original_allocation)


if __name__ == "__main__":
    unittest.main()
