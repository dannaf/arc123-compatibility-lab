from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
P0023_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0023_arc12_development_baseline_40"
P0024_PACKET_PATH = (
    REPOSITORY_ROOT
    / "research"
    / "packets"
    / "P0024_ARC12_PANEL_STREAM_FRACTAL_DEVELOPMENT_40.json"
)
P0024_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0024_arc12_panel_stream_fractal_development_40"
P0025_PACKET_PATH = (
    REPOSITORY_ROOT
    / "research"
    / "packets"
    / "P0025_ARC12_HIDDEN_ZERO_STREAM_DEVELOPMENT_40.json"
)
P0025_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0025_arc12_hidden_zero_stream_development_40"
P0024_SOLVES = {
    ("arc1", "cf98881b"),
    ("arc1", "c8f0f002"),
    ("arc1", "c3e719e8"),
    ("arc1", "73182012"),
    ("arc1", "1a6449f1"),
    ("arc2", "80af3007"),
}
P0025_SOLVES = {*P0024_SOLVES, ("arc1", "feca6190")}

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0024P0025DevelopmentTests(unittest.TestCase):
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

    def _assert_reports(
        self,
        packet: dict,
        report_root: Path,
        expected_solves: set[tuple[str, str]],
    ) -> None:
        summary = json.loads((report_root / "receipt.json").read_text(encoding="utf-8"))
        tasks = packet_runner._task_records(packet)
        self.assertEqual(len(tasks), 40)
        for task in tasks:
            key = (task["benchmark"], task["task_id"])
            report_directory = report_root / task["benchmark"] / task["task_id"]
            receipt = json.loads((report_directory / "receipt.json").read_text(encoding="utf-8"))
            report = (report_directory / "REPORT.md").read_text(encoding="utf-8")
            trace = json.loads((report_directory / "learning_trace.json").read_text(encoding="utf-8"))
            diagram = (report_directory / "corpus_callosum.svg").read_text(encoding="utf-8")

            self.assertEqual(receipt["all_cells_match"], key in expected_solves)
            self.assertEqual(receipt["frozen_controller"], summary["frozen_controller"])
            self.assertEqual(receipt["controller_oracle_boundary_scan"], "pass")
            self.assertTrue(all(value is False for value in receipt["agent_input_contract"].values()))
            self.assertIn("Expected output (post-answer only)", report)
            self.assertIn(
                "Outcome: YES — ALL TEST CELLS MATCH"
                if key in expected_solves
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

    def test_p0024_portfolio_is_complete_and_adds_three_same_cohort_results(self) -> None:
        packet = json.loads(P0024_PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((P0024_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        baseline = json.loads((P0023_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (P0024_REPORT_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(summary["attempt_count"], 40)
        self.assertEqual(summary["exact_solve_count"], 6)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 5, "arc2": 1})
        self.assertEqual(summary["complete_wrong_count"], 34)
        self.assertEqual(summary["training_exact_count"], 6)
        self.assertEqual(summary["fallback_count"], 34)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(packet["baseline_reference"]["exact_solve_count"], 3)
        self.assertEqual(baseline["exact_solve_count"], 3)
        self.assertTrue(
            all(
                value is False
                for value in packet["offline_diagnostic_provenance"]["live_controller_boundary"].values()
            )
        )
        self.assertIn("Exact post-answer solves: `6/40`", readme)
        self.assertTrue(
            {
                "separated_panel_cellwise_combine",
                "anti_diagonal_nonbackground_stream",
                "symmetric_foreground_quadrant_crop",
                "uniform_block_self_stamp_fractal",
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
        self.assertEqual(actual_solves, P0024_SOLVES)
        self.assertEqual(
            actual_solves - baseline_solves,
            {("arc1", "cf98881b"), ("arc1", "73182012"), ("arc2", "80af3007")},
        )
        selected = {
            (entry["benchmark"], entry["task_id"]): entry["selected_hypothesis"]
            for entry in summary["attempts"]
        }
        self.assertIn("separated_panel_cellwise_combine(axis=vertical", selected[("arc1", "cf98881b")])
        self.assertEqual(
            selected[("arc1", "73182012")],
            "symmetric_foreground_quadrant_crop(quadrant=top_left)",
        )
        self.assertEqual(selected[("arc2", "80af3007")], "uniform_block_self_stamp_fractal")
        self._assert_reports(packet, P0024_REPORT_ROOT, P0024_SOLVES)

    def test_p0025_hidden_zero_correction_is_complete_and_keeps_p0024_intact(self) -> None:
        packet = json.loads(P0025_PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((P0025_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        baseline = json.loads((P0024_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (P0025_REPORT_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(summary["attempt_count"], 40)
        self.assertEqual(summary["exact_solve_count"], 7)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 6, "arc2": 1})
        self.assertEqual(summary["complete_wrong_count"], 33)
        self.assertEqual(summary["training_exact_count"], 7)
        self.assertEqual(summary["fallback_count"], 33)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(packet["baseline_reference"]["exact_solve_count"], 6)
        self.assertEqual(baseline["exact_solve_count"], 6)
        boundary = packet["offline_diagnostic_provenance"]["live_controller_boundary"]
        self.assertTrue(boundary["development_post_answer_target_inspected_during_rnd"])
        self.assertFalse(boundary["held_out_output_available_to_live_agent_before_commit"])
        self.assertFalse(boundary["gt_feature_contract_passed_to_agent"])
        self.assertFalse(boundary["gt_solver_imported_or_called"])
        self.assertIn("Exact post-answer solves: `7/40`", readme)
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
        self.assertEqual(actual_solves, P0025_SOLVES)
        self.assertEqual(actual_solves - baseline_solves, {("arc1", "feca6190")})
        selected = {
            (entry["benchmark"], entry["task_id"]): entry["selected_hypothesis"]
            for entry in summary["attempts"]
        }
        self.assertEqual(
            selected[("arc1", "feca6190")],
            "anti_diagonal_nonbackground_stream(background_color=0)",
        )
        self._assert_reports(packet, P0025_REPORT_ROOT, P0025_SOLVES)


if __name__ == "__main__":
    unittest.main()
