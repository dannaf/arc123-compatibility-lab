from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import freeze_arc12_filename_holdout as standard_freezer
import freeze_arc12_mixed_partition_development as mixed_freezer


class FilenameMixedPartitionDevelopmentFreezerTests(unittest.TestCase):
    def _inventory(self, benchmark: str) -> list[dict[str, str]]:
        return [
            {
                "benchmark": benchmark,
                "split": split,
                "task_id": f"{benchmark}-{split}-{index}",
                "source_path": str(REPOSITORY_ROOT / "README.md"),
            }
            for split in ("evaluation", "training")
            for index in range(3)
        ]

    def test_manifest_selects_the_declared_mixed_partitions(self) -> None:
        inventories = {benchmark: self._inventory(benchmark) for benchmark in ("arc1", "arc2")}
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
            manifest = mixed_freezer._manifest(
                REPOSITORY_ROOT / "arc1-source",
                REPOSITORY_ROOT / "arc2-source",
                "https://example.com/arc1",
                "https://example.com/arc2",
                (),
                "synthetic-salt",
                "SYNTHETIC",
                "Synthetic mixed partition",
                "synthetic_mixed_4",
                "synthetic boundary",
                {"arc1": "evaluation", "arc2": "training"},
                2,
            )

        frozen = manifest["synthetic_mixed_4"]
        self.assertEqual(frozen["task_count"], 4)
        self.assertEqual(frozen["per_benchmark_task_count"], 2)
        self.assertTrue(
            all(record["split"] == "evaluation" for record in frozen["tasks"]["arc1"])
        )
        self.assertTrue(
            all(record["split"] == "training" for record in frozen["tasks"]["arc2"])
        )
        self.assertEqual(
            frozen["selection_protocol"]["selection_metadata"]["arc1"]["split_allocation"],
            {"evaluation": 2},
        )
        self.assertEqual(
            frozen["selection_protocol"]["selection_metadata"]["arc2"]["split_allocation"],
            {"training": 2},
        )
        self.assertTrue(all(value is False for value in manifest["live_controller_boundary"].values()))

    def test_manifest_refuses_insufficient_declared_partition(self) -> None:
        inventories = {
            "arc1": [record for record in self._inventory("arc1") if record["split"] == "evaluation"][:1],
            "arc2": self._inventory("arc2"),
        }
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
        ), self.assertRaises(ValueError):
            mixed_freezer._manifest(
                REPOSITORY_ROOT / "arc1-source",
                REPOSITORY_ROOT / "arc2-source",
                "https://example.com/arc1",
                "https://example.com/arc2",
                (),
                "synthetic-salt",
                "SYNTHETIC",
                "Synthetic mixed partition",
                "synthetic_mixed_4",
                "synthetic boundary",
                {"arc1": "evaluation", "arc2": "training"},
                2,
            )


if __name__ == "__main__":
    unittest.main()
