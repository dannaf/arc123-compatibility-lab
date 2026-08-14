from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as element_tree
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = (
    REPOSITORY_ROOT
    / "research"
    / "packets"
    / "P0034_ARC12_SHARED_BACKGROUND_PANEL_DEVELOPMENT_40.json"
)
BASELINE_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0033_arc12_training_development_baseline_40"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0034_arc12_shared_background_panel_development_40"
BASELINE_SOLVES = {
    ("arc1", "67e8384a"),
    ("arc2", "b1948b0a"),
    ("arc2", "506d28a5"),
}
EXPECTED_SOLVES = {*BASELINE_SOLVES, ("arc2", "a87f7484")}

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0034SharedBackgroundPanelDevelopmentTests(unittest.TestCase):
    def _pinned_bytes(self, commit: str, raw_path: str) -> bytes:
        return subprocess.run(
            ["git", "-C", str(REPOSITORY_ROOT), "show", f"{commit}:{raw_path}"],
            check=True,
            capture_output=True,
        ).stdout

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
            self.assertEqual(
                hashlib.sha256(self._pinned_bytes(frozen_commit, raw_path)).hexdigest(),
                expected_hash,
            )

    def test_p0034_preserves_p0033_and_retains_complete_vv_artifacts(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        baseline = json.loads(
            (BASELINE_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8")
        )
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(packet["implementation_commit"], packet["frozen_controller"]["commit"])
        self.assertEqual(summary["attempt_count"], 40)
        self.assertEqual(len(tasks), 40)
        self.assertEqual(summary["exact_solve_count"], 4)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 1, "arc2": 3})
        self.assertEqual(summary["complete_wrong_count"], 36)
        self.assertEqual(summary["training_exact_count"], 5)
        self.assertEqual(summary["fallback_count"], 35)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(packet["baseline_reference"]["exact_solve_count"], 3)
        self.assertEqual(baseline["exact_solve_count"], 3)
        self.assertEqual(
            hashlib.sha256((BASELINE_REPORT_ROOT / "receipt.json").read_bytes()).hexdigest(),
            packet["baseline_reference"]["receipt_sha256"],
        )
        boundary = packet["offline_diagnostic_provenance"]["live_controller_boundary"]
        self.assertTrue(boundary["development_post_answer_target_inspected_during_rnd"])
        self.assertFalse(boundary["held_out_output_available_to_live_agent_before_commit"])
        self.assertFalse(boundary["gt_feature_contract_passed_to_agent"])
        self.assertFalse(boundary["gt_solver_imported_or_called"])
        self.assertIn("Exact post-answer solves: `4/40`", readme)
        self.assertIn(
            "repeated_panel_odd_one_out_crop",
            packet["frozen_controller"]["generic_operator_families"],
        )
        synthetic = packet["synthetic_contract"]
        self.assertEqual(
            hashlib.sha256(
                self._pinned_bytes(packet["implementation_commit"], synthetic["test_path"])
            ).hexdigest(),
            synthetic["test_sha256"],
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
        self.assertEqual(baseline_solves, BASELINE_SOLVES)
        self.assertEqual(actual_solves, EXPECTED_SOLVES)
        self.assertEqual(actual_solves - baseline_solves, {("arc2", "a87f7484")})

        selected = {
            (entry["benchmark"], entry["task_id"]): entry["selected_hypothesis"]
            for entry in summary["attempts"]
        }
        self.assertEqual(
            selected[("arc2", "a87f7484")],
            "repeated_panel_odd_one_out_crop(output_height=3,output_width=3)",
        )

        for task in tasks:
            key = (task["benchmark"], task["task_id"])
            report_directory = REPORT_ROOT / task["benchmark"] / task["task_id"]
            receipt = json.loads(
                (report_directory / "receipt.json").read_text(encoding="utf-8")
            )
            report = (report_directory / "REPORT.md").read_text(encoding="utf-8")
            trace = json.loads(
                (report_directory / "learning_trace.json").read_text(encoding="utf-8")
            )
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
            self.assertIn("Committed output", diagram)
            self.assertIn("Compatibility core", diagram)
            if key == ("arc2", "a87f7484"):
                self.assertIn("odd repeated-panel crop", diagram)
            element_tree.fromstring(diagram)

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
                self.assertEqual(
                    test_case["all_cells_match"],
                    prediction == test_case["expected_output"],
                )
            for artifact in receipt["trace_artifacts"].values():
                artifact_path = report_directory / artifact["path"]
                self.assertEqual(
                    hashlib.sha256(artifact_path.read_bytes()).hexdigest(), artifact["sha256"]
                )


if __name__ == "__main__":
    unittest.main()
