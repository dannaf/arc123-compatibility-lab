from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0004_ARC3_REAL_TRANSITION_PROBE.json"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0004_arc3_real_transition_probe" / "ls20_L1"


class ARC3TransitionEvidenceTests(unittest.TestCase):
    def test_real_transition_packet_retains_causal_shared_core_evidence(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        receipt = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        report = (REPORT_ROOT / "REPORT.md").read_text(encoding="utf-8")
        trace = json.loads((REPORT_ROOT / "learning_trace.json").read_text(encoding="utf-8"))
        diagram = (REPORT_ROOT / "corpus_callosum.svg").read_text(encoding="utf-8")

        self.assertEqual(receipt["packet_id"], packet["packet_id"])
        self.assertEqual(receipt["source_pin"]["commit"], packet["source_pin"]["commit"])
        self.assertEqual(receipt["source_pin"]["path"], packet["source_pin"]["path"])
        self.assertTrue(receipt["external_probe_confirmed"])
        self.assertEqual(receipt["transition_count"], 2)
        self.assertTrue(all(item["accepted"] for item in receipt["transitions"]))
        self.assertTrue(all(item["changed"] is True for item in receipt["transitions"]))
        self.assertEqual(
            receipt["selected_hypothesis"], "environment_transition(effect=state_change_possible)"
        )
        self.assertIn("ARC3 level solved:** `NO CLAIM`", report)
        self.assertIn("not a game-solving result", report)

        actions = [event["action"] for event in trace["events"]]
        self.assertLess(actions.index("PROPOSE"), actions.index("FIND_COUNTEREXAMPLE"))
        self.assertLess(actions.index("FIND_COUNTEREXAMPLE"), actions.index("SPECIALIZE"))
        self.assertLess(actions.index("SPECIALIZE"), actions.index("COMMIT"))

        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', diagram)
        self.assertIn("Observed state before probe", diagram)
        self.assertIn("Observed state after probe", diagram)
        self.assertIn("Shared compatibility core", diagram)
        self.assertIn("ACTION1", diagram)
        self.assertIn("H1: selected action is static", diagram)
        self.assertIn("H2: state change is possible", diagram)
        self.assertIn('stroke="#e11d48"', diagram)


if __name__ == "__main__":
    unittest.main()
