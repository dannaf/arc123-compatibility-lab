from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0009_ARC3_LEARNED_MECHANICS_L1.json"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0009_arc3_learned_mechanics" / "ls20_L1"


class P0009ARC3MechanicsEvidenceTests(unittest.TestCase):
    def test_p0009_is_complete_reproducible_and_bounded(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        receipt = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        report = (REPORT_ROOT / "REPORT.md").read_text(encoding="utf-8")
        trace = json.loads((REPORT_ROOT / "learning_trace.json").read_text(encoding="utf-8"))
        diagram = (REPORT_ROOT / "corpus_callosum.svg").read_text(encoding="utf-8")

        self.assertEqual(receipt["packet_id"], packet["packet_id"])
        self.assertTrue(receipt["acceptance_passed"])
        self.assertEqual(receipt["history_transition_count"], 15)
        self.assertEqual(receipt["learned_action_effect_count"], 4)
        self.assertTrue(receipt["mechanics_learning_confirmed"])
        self.assertTrue(receipt["goal_directed_action_confirmed"])
        self.assertTrue(receipt["non_default_action_confirmed"])
        self.assertTrue(receipt["goal_distance_reduction_confirmed"])
        self.assertTrue(receipt["level_progress_observed"])
        self.assertEqual((receipt["initial_progress"], receipt["final_progress"]), (0.0, 1.0))
        self.assertEqual(receipt["controller_oracle_boundary_scan"], "pass")
        self.assertTrue(all(value is False for value in receipt["agent_input_contract"].values()))
        self.assertEqual(
            [effect["key"] for effect in receipt["final_theory"]["learned_motion_model"]["action_effects"]],
            ["ACTION1", "ACTION2", "ACTION3", "ACTION4"],
        )
        self.assertEqual(len(receipt["action_choices"]), packet["controller"]["max_actions"])
        self.assertTrue(receipt["action_choices"][0]["is_non_default"])
        self.assertTrue(
            all(
                choice["goal_distance_after"] < choice["goal_distance_before"]
                and choice["prediction_matched_observation"]
                for choice in receipt["action_choices"]
            )
        )
        self.assertIn("## Outcome: YES", report)
        self.assertIn("**General ARC3 / ARC-AGI solver claim:** `NO`", report)
        self.assertIn("Bounded public history", diagram)
        self.assertGreaterEqual(len(trace["events"]), 20)

        for artifact in receipt["trace_artifacts"].values():
            artifact_path = REPORT_ROOT / artifact["path"]
            actual_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            self.assertEqual(actual_hash, artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
