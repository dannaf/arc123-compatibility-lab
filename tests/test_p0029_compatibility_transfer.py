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
    / "P0029_ARC12_COMPATIBILITY_PORTFOLIO_TRAINING_TRANSFER_50.json"
)
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0029_arc12_compatibility_portfolio_training_transfer_50"
EXPECTED_SOLVES = {
    ("arc1", "8d5021e8"),
    ("arc1", "6150a2bd"),
    ("arc1", "c9e6f938"),
    ("arc2", "6d0aefbc"),
}
P0028_NEW_RELATIONS = {
    "distinct_color_scale",
    "quadrant_odd_one_out",
    "singleton_foreground_border",
    "distinct_color_count_line",
}

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0029CompatibilityTransferTests(unittest.TestCase):
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

    def test_p0029_fresh_transfer_is_complete_and_failure_inclusive(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(summary["attempt_count"], 50)
        self.assertEqual(len(tasks), 50)
        self.assertEqual(summary["exact_solve_count"], 4)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 3, "arc2": 1})
        self.assertEqual(summary["complete_wrong_count"], 46)
        self.assertEqual(summary["training_exact_count"], 4)
        self.assertEqual(summary["fallback_count"], 46)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertIn("Exact post-answer solves: `4/50`", readme)
        self.assertEqual({task["split"] for task in tasks}, {"training"})
        self.assertEqual(
            packet["implementation_reference"]["frozen_controller_commit"],
            packet["frozen_controller"]["commit"],
        )
        self.assertIn(
            "not a denominator or statistical baseline",
            packet["implementation_reference"]["comparison_boundary"],
        )
        boundary = packet["offline_diagnostic_provenance"]["live_controller_boundary"]
        self.assertTrue(all(value is False for value in boundary.values()))
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
        self.assertIn("dihedral_tile", selected[("arc1", "8d5021e8")])
        self.assertEqual(selected[("arc1", "6150a2bd")], "rotate_180(scope=all)")
        self.assertIn("dihedral_tile", selected[("arc1", "c9e6f938")])
        self.assertIn("dihedral_tile", selected[("arc2", "6d0aefbc")])
        self.assertTrue(
            all(
                relation not in selected[key]
                for key in EXPECTED_SOLVES
                for relation in P0028_NEW_RELATIONS
            )
        )

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
