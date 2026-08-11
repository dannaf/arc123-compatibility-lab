from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0001_ARC12_TINY_REDISCOVERY.json"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0001_arc12_tiny_rediscovery"


class P0001EvidenceTests(unittest.TestCase):
    def test_every_preregistered_attempt_has_complete_yes_or_no_vv_evidence(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(summary["attempt_count"], len(packet["tasks"]))
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(
            {(entry["benchmark"], entry["task_id"]) for entry in summary["attempts"]},
            {(entry["benchmark"], entry["task_id"]) for entry in packet["tasks"]},
        )
        for task in packet["tasks"]:
            report_directory = REPORT_ROOT / task["benchmark"] / task["task_id"]
            receipt = json.loads((report_directory / "receipt.json").read_text(encoding="utf-8"))
            report = (report_directory / "REPORT.md").read_text(encoding="utf-8")
            self.assertIsInstance(receipt["all_cells_match"], bool)
            self.assertGreater(receipt["compared_position_count"], 0)
            self.assertIsInstance(receipt["test_cases"], list)
            self.assertTrue(receipt["test_cases"])
            self.assertTrue(
                all(isinstance(case["prediction"], list) for case in receipt["test_cases"])
            )
            self.assertEqual(receipt["controller_oracle_boundary_scan"], "pass")
            self.assertTrue(
                all(value is False for value in receipt["agent_input_contract"].values())
            )
            self.assertIn("## Outcome: YES" if receipt["all_cells_match"] else "## Outcome: NO", report)
            self.assertTrue((report_directory / "learning_trace.json").is_file())
            self.assertTrue((report_directory / "corpus_callosum.svg").is_file())


if __name__ == "__main__":
    unittest.main()
