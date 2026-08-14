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
    / "P0036_ARC12_TRAINING_DEVELOPMENT_BASELINE_40.json"
)
P0035_PACKET_PATH = (
    REPOSITORY_ROOT
    / "research"
    / "packets"
    / "P0035_ARC12_SHARED_BACKGROUND_PANEL_TRAINING_TRANSFER_50.json"
)
P0035_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0035_arc12_shared_background_panel_training_transfer_50"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0036_arc12_training_development_baseline_40"
EXPECTED_SOLVES = {
    ("arc1", "2dc579da"),
    ("arc2", "5d2a5c43"),
}

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0036TrainingDevelopmentBaselineTests(unittest.TestCase):
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

    def test_p0036_retains_complete_development_baseline_artifacts(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        p0035_packet = json.loads(P0035_PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        p0035_summary = json.loads((P0035_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(packet["implementation_commit"], packet["frozen_controller"]["commit"])
        self.assertEqual(summary["attempt_count"], 40)
        self.assertEqual(len(tasks), 40)
        self.assertEqual(summary["exact_solve_count"], 2)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 1, "arc2": 1})
        self.assertEqual(summary["complete_wrong_count"], 38)
        self.assertEqual(summary["training_exact_count"], 2)
        self.assertEqual(summary["fallback_count"], 38)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(packet["cohort_import"]["task_count"], 40)
        self.assertEqual(packet["cohort_import"]["per_benchmark_task_count"], 20)
        self.assertEqual(packet["prior_transfer_reference"]["exact_solve_count"], 3)
        self.assertEqual(p0035_summary["exact_solve_count"], 3)
        self.assertEqual(p0035_summary["attempt_count"], 50)
        self.assertIn("Exact post-answer solves: `2/40`", readme)
        self.assertIn(
            "repeated_panel_odd_one_out_crop",
            packet["frozen_controller"]["generic_operator_families"],
        )
        self.assertTrue(
            all(
                value is False
                for value in packet["offline_diagnostic_provenance"][
                    "live_controller_boundary"
                ].values()
            )
        )
        self.assertEqual(
            packet["frozen_controller"]["commit"],
            p0035_packet["frozen_controller"]["commit"],
        )
        common_source_files = set(packet["frozen_controller"]["source_files"]) & set(
            p0035_packet["frozen_controller"]["source_files"]
        )
        for raw_path in common_source_files:
            self.assertEqual(
                packet["frozen_controller"]["source_files"][raw_path],
                p0035_packet["frozen_controller"]["source_files"][raw_path],
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
        self.assertEqual(actual_solves, EXPECTED_SOLVES)
        selected = {
            (entry["benchmark"], entry["task_id"]): entry["selected_hypothesis"]
            for entry in summary["attempts"]
        }
        self.assertEqual(selected[("arc1", "2dc579da")], "quadrant_odd_one_out")
        self.assertIn(
            "central_separator_cellwise_combine",
            selected[("arc2", "5d2a5c43")],
        )
        self.assertFalse(
            any(
                "repeated_panel_odd_one_out_crop" in entry["selected_hypothesis"]
                for entry in summary["attempts"]
            )
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
            self.assertIn('viewBox="0 0 1280 620"', diagram)
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
