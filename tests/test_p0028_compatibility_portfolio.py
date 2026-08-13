from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = (
    REPOSITORY_ROOT
    / "research"
    / "packets"
    / "P0028_ARC12_COMPATIBILITY_PORTFOLIO_DEVELOPMENT_40.json"
)
BASELINE_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0027_arc12_development_baseline_40"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0028_arc12_compatibility_portfolio_development_40"
EXPECTED_SOLVES = {
    ("arc1", "88a62173"),
    ("arc1", "d4b1c2b1"),
    ("arc1", "a416b8f3"),
    ("arc1", "25ff71a9"),
    ("arc2", "d19f7514"),
    ("arc2", "0d3d703e"),
    ("arc2", "6e02f1e3"),
    ("arc2", "fc754716"),
}
NEW_SOLVES = {
    ("arc1", "88a62173"),
    ("arc1", "d4b1c2b1"),
    ("arc1", "25ff71a9"),
    ("arc2", "6e02f1e3"),
    ("arc2", "fc754716"),
}

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0028CompatibilityPortfolioTests(unittest.TestCase):
    def _assert_frozen_controller_bytes(self, packet: dict) -> None:
        frozen_controller = packet["frozen_controller"]
        frozen_commit = frozen_controller["commit"]
        resolved = subprocess.run(
            ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", f"{frozen_commit}^{{commit}}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(resolved, frozen_commit)
        for raw_path, expected_hash in frozen_controller["source_files"].items():
            pinned_bytes = subprocess.run(
                ["git", "-C", str(REPOSITORY_ROOT), "show", f"{frozen_commit}:{raw_path}"],
                check=True,
                capture_output=True,
            ).stdout
            self.assertEqual(hashlib.sha256(pinned_bytes).hexdigest(), expected_hash)

    def test_p0028_portfolio_is_complete_and_preserves_the_p0027_denominator(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        baseline = json.loads((BASELINE_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(summary["attempt_count"], 40)
        self.assertEqual(len(tasks), 40)
        self.assertEqual(summary["exact_solve_count"], 8)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 4, "arc2": 4})
        self.assertEqual(summary["complete_wrong_count"], 32)
        self.assertEqual(summary["training_exact_count"], 8)
        self.assertEqual(summary["fallback_count"], 32)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(packet["baseline_reference"]["exact_solve_count"], 3)
        self.assertEqual(baseline["exact_solve_count"], 3)
        boundary = packet["offline_diagnostic_provenance"]["live_controller_boundary"]
        self.assertTrue(boundary["development_post_answer_target_inspected_during_rnd"])
        self.assertFalse(boundary["held_out_output_available_to_live_agent_before_commit"])
        self.assertFalse(boundary["gt_feature_contract_passed_to_agent"])
        self.assertFalse(boundary["gt_solver_imported_or_called"])
        self.assertIn("Exact post-answer solves: `8/40`", readme)
        self.assertTrue(
            {
                "distinct_color_scale",
                "quadrant_odd_one_out",
                "singleton_foreground_border",
                "distinct_color_count_line",
            }.issubset(packet["frozen_controller"]["generic_operator_families"])
        )
        self._assert_frozen_controller_bytes(packet)

        actual_solves = {
            (entry["benchmark"], entry["task_id"])
            for entry in summary["attempts"]
            if entry["all_cells_match"]
        }
        baseline_solves = {
            (entry["benchmark"], entry["task_id"])
            for entry in baseline["attempts"]
            if entry["all_cells_match"]
        }
        self.assertEqual(actual_solves, EXPECTED_SOLVES)
        self.assertEqual(actual_solves - baseline_solves, NEW_SOLVES)

        selected = {
            (entry["benchmark"], entry["task_id"]): entry["selected_hypothesis"]
            for entry in summary["attempts"]
        }
        self.assertEqual(selected[("arc1", "88a62173")], "quadrant_odd_one_out")
        self.assertEqual(selected[("arc1", "d4b1c2b1")], "distinct_color_scale")
        self.assertEqual(selected[("arc1", "25ff71a9")], "translate(column_offset=0,row_offset=1)")
        self.assertIn("distinct_color_count_line", selected[("arc2", "6e02f1e3")])
        self.assertEqual(selected[("arc2", "fc754716")], "singleton_foreground_border")

        for task in tasks:
            key = (task["benchmark"], task["task_id"])
            report_directory = REPORT_ROOT / task["benchmark"] / task["task_id"]
            receipt = json.loads((report_directory / "receipt.json").read_text(encoding="utf-8"))
            report = (report_directory / "REPORT.md").read_text(encoding="utf-8")
            trace = json.loads((report_directory / "learning_trace.json").read_text(encoding="utf-8"))
            diagram = (report_directory / "corpus_callosum.svg").read_text(encoding="utf-8")

            self.assertEqual(receipt["all_cells_match"], key in EXPECTED_SOLVES)
            self.assertEqual(receipt["frozen_controller"], summary["frozen_controller"])
            self.assertEqual(receipt["controller_oracle_boundary_scan"], "pass")
            self.assertTrue(all(value is False for value in receipt["agent_input_contract"].values()))
            self.assertIn("Expected output (post-answer only)", report)
            self.assertIn(
                "Outcome: YES — ALL TEST CELLS MATCH"
                if key in EXPECTED_SOLVES
                else "Outcome: NO — TEST CELLS DO NOT ALL MATCH",
                report,
            )
            self.assertTrue(trace["events"])
            self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', diagram)
            self.assertIn("Committed output", diagram)
            self.assertIn("Compatibility core", diagram)

            for test_case in receipt["test_cases"]:
                prediction = test_case["prediction"]
                self.assertTrue(prediction)
                self.assertTrue(
                    all(
                        prediction_row
                        and len(prediction_row) == len(prediction[0])
                        and all(isinstance(cell, int) for cell in prediction_row)
                        for prediction_row in prediction
                    )
                )
                self.assertEqual(test_case["all_cells_match"], prediction == test_case["expected_output"])
            for artifact in receipt["trace_artifacts"].values():
                artifact_path = report_directory / artifact["path"]
                self.assertEqual(hashlib.sha256(artifact_path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
