from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_holdout as standard_freezer
import freeze_arc12_filename_training_development as development_freezer
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

    def test_development_wrapper_scopes_training_only_configuration(self) -> None:
        original_allocation = dict(standard_freezer.DEFAULT_ALLOCATION)
        observed: dict[str, object] = {}

        def inspect_configuration() -> int:
            observed["allocation"] = dict(standard_freezer.DEFAULT_ALLOCATION)
            observed["salt"] = standard_freezer.DEFAULT_SALT
            observed["cohort_key"] = standard_freezer.DEFAULT_COHORT_KEY
            return 23

        with mock.patch.object(standard_freezer, "main", side_effect=inspect_configuration):
            self.assertEqual(development_freezer.main(), 23)

        self.assertEqual(observed["allocation"], {"training": 20})
        self.assertEqual(observed["salt"], development_freezer.DEFAULT_SALT)
        self.assertEqual(observed["cohort_key"], development_freezer.DEFAULT_COHORT_KEY)
        self.assertEqual(standard_freezer.DEFAULT_ALLOCATION, original_allocation)

    def test_manifest_uses_the_requested_allocation_for_task_count(self) -> None:
        source_path = str(REPOSITORY_ROOT / "README.md")
        inventories = {
            "arc1": [
                {
                    "benchmark": "arc1",
                    "split": "training",
                    "task_id": "arc1-first",
                    "source_path": source_path,
                },
                {
                    "benchmark": "arc1",
                    "split": "training",
                    "task_id": "arc1-second",
                    "source_path": source_path,
                },
            ],
            "arc2": [
                {
                    "benchmark": "arc2",
                    "split": "training",
                    "task_id": "arc2-first",
                    "source_path": source_path,
                },
                {
                    "benchmark": "arc2",
                    "split": "training",
                    "task_id": "arc2-second",
                    "source_path": source_path,
                },
            ],
        }
        original_allocation = standard_freezer.DEFAULT_ALLOCATION
        try:
            standard_freezer.DEFAULT_ALLOCATION = {"training": 2}
            with mock.patch.object(
                standard_freezer,
                "_excluded_task_ids_from_imports",
                return_value=(set(), []),
            ), mock.patch.object(
                standard_freezer,
                "_filename_inventory",
                side_effect=lambda _source_root, benchmark: inventories[benchmark],
            ), mock.patch.object(
                standard_freezer,
                "_verify_clean_source",
                return_value="source-pin",
            ):
                manifest = standard_freezer._manifest(
                    REPOSITORY_ROOT / "arc1-source",
                    REPOSITORY_ROOT / "arc2-source",
                    "https://example.com/arc1",
                    "https://example.com/arc2",
                    (),
                    "synthetic-salt",
                    "SYNTHETIC",
                    "Synthetic cohort",
                    "synthetic_4",
                    "synthetic boundary",
                )
        finally:
            standard_freezer.DEFAULT_ALLOCATION = original_allocation

        frozen = manifest["synthetic_4"]
        self.assertEqual(frozen["task_count"], 4)
        self.assertEqual(frozen["per_benchmark_task_count"], 2)


if __name__ == "__main__":
    unittest.main()
