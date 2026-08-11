from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.oracles import validate_arc12_ihl_gt_pilot, validate_arc3_ihl_gt_inventory


ARC12_PILOT = (
    REPOSITORY_ROOT / "research" / "oracle_materializations" / "ARC12_IHL_GT_PILOT_001.json"
)
ARC3_INVENTORY = (
    REPOSITORY_ROOT / "research" / "oracle_materializations" / "ARC3_IHL_GT_INVENTORY_001.json"
)


class OracleMaterializationTests(unittest.TestCase):
    def test_arc12_pilot_has_four_source_pinned_offline_records(self) -> None:
        payload = json.loads(ARC12_PILOT.read_text(encoding="utf-8"))
        summary = validate_arc12_ihl_gt_pilot(payload)

        self.assertEqual(summary, {"record_count": 4, "benchmark_count": 2})
        self.assertEqual(payload["source_pin"]["commit"], "525000ab1f78fb1e66906149f72f6e8eac34ab71")
        self.assertTrue(
            all(value is False for value in payload["live_agent_boundary"].values())
        )
        for record in payload["records"]:
            self.assertTrue(record["offline_only"])
            self.assertFalse(record["live_agent_input"])
            self.assertFalse(record["steps"][0]["prediction"]["answer_grid_included"])
            self.assertIn("final_program", record)

    def test_arc3_inventory_classifies_all_audited_entries_and_records_both_pins(self) -> None:
        payload = json.loads(ARC3_INVENTORY.read_text(encoding="utf-8"))
        summary = validate_arc3_ihl_gt_inventory(payload)

        self.assertEqual(summary["inventory_count"], 10)
        self.assertEqual(summary["classification_count"], 5)
        self.assertEqual(summary["asset_count"], 121)
        self.assertEqual(payload["source_pin"]["commit"], "d32b91e6b442079fbd46f0cd17c608485032d278")
        self.assertEqual(
            payload["audited_asset_snapshot"]["commit"],
            "c0f27916881071fe4c9f622383d5c47a3bcc05ab",
        )
        self.assertTrue(payload["live_agent_boundary"]["oracle_comparison_only_after_run"])
        self.assertTrue(
            all(item["live_learner_access"] is False for item in payload["asset_inventory"])
        )

    def test_live_controller_and_adapters_do_not_import_offline_materialization_readers(self) -> None:
        live_sources = [
            REPOSITORY_ROOT / "src" / "arc123" / "controller.py",
            REPOSITORY_ROOT / "src" / "arc123" / "adapters" / "arc12.py",
            REPOSITORY_ROOT / "src" / "arc123" / "adapters" / "arc3.py",
        ]
        for source in live_sources:
            with self.subTest(source=source.name):
                content = source.read_text(encoding="utf-8")
                self.assertNotIn("from ..oracles", content)
                self.assertNotIn("from .oracles", content)
                self.assertNotIn("oracle_materializations", content)


if __name__ == "__main__":
    unittest.main()
