from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0007_ARC12_CONDITIONAL_REVISION_10.json"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0007_arc12_conditional_revision_10"


class P0007RevisionEvidenceTests(unittest.TestCase):
    def test_p0007_reports_are_complete_and_gate_the_frozen_cohort(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(summary["attempt_count"], 10)
        self.assertEqual(summary["exact_solve_count"], 3)
        self.assertEqual(summary["complete_wrong_count"], 7)
        self.assertEqual(summary["causal_acceptance_count"], 3)
        self.assertEqual(summary["ablation_exact_counts"], {
            "no_new_residual_family": 0,
            "no_revision": 0,
        })
        self.assertTrue(summary["frozen_generalization_gate"]["passed"])
        self.assertEqual(
            set(summary["generic_families_in_exact_results"]),
            {
                "component_property_erase",
                "component_property_recolor",
                "marker_shape_target_recolor",
                "row_span_minimum",
            },
        )
        self.assertIn("Frozen 25+25 gate: `PASS`", readme)

        exact_task_ids = {
            attempt["task_id"]
            for attempt in summary["attempts"]
            if attempt["all_cells_match"]
        }
        self.assertEqual(exact_task_ids, {"009d5c81", "5ad8a7c0", "a09f6c25"})

        for attempt in summary["attempts"]:
            report_directory = REPORT_ROOT / attempt["benchmark"] / attempt["task_id"]
            receipt = json.loads((report_directory / "receipt.json").read_text(encoding="utf-8"))
            report = (report_directory / "REPORT.md").read_text(encoding="utf-8")
            trace = json.loads((report_directory / "learning_trace.json").read_text(encoding="utf-8"))
            diagram = (report_directory / "corpus_callosum.svg").read_text(encoding="utf-8")

            self.assertEqual(receipt["all_cells_match"], attempt["all_cells_match"])
            self.assertEqual(receipt["controller_oracle_boundary_scan"], "pass")
            self.assertIn("Expected output (post-answer only)", report)
            outcome = (
                "YES — ALL TEST CELLS MATCH"
                if receipt["all_cells_match"]
                else "NO — TEST CELLS DO NOT ALL MATCH"
            )
            self.assertIn(outcome, report)
            self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', diagram)
            self.assertTrue(trace["events"])

            for artifact in receipt["trace_artifacts"].values():
                artifact_path = report_directory / artifact["path"]
                actual_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                self.assertEqual(actual_hash, artifact["sha256"])

            if receipt["all_cells_match"]:
                self.assertTrue(receipt["causal_trace"]["accepted"])
                actions = [event["action"] for event in trace["events"]]
                self.assertIn("FIND_COUNTEREXAMPLE", actions)
                self.assertIn("COMPOSE_RULE", actions)
                self.assertIn("PROMOTE_CONSTRAINT", actions)
            else:
                self.assertFalse(receipt["causal_trace"]["accepted"])


if __name__ == "__main__":
    unittest.main()
