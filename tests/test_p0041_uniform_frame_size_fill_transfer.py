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
    / "P0041_ARC12_UNIFORM_FRAME_SIZE_FILL_FINAL_TRAINING_TRANSFER_38.json"
)
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0041_arc12_uniform_frame_size_fill_final_training_transfer_38"
EXPECTED_SOLVES = {("arc1", "94f9d214")}
EXPECTED_HYPOTHESIS = (
    "adjacent_bilateral_cellwise_combine("
    "axis=horizontal,table=0:0:2;0:1:0;3:0:0;3:1:0)"
)
LIVE_ANSWER_SOURCE_FILES = (
    "scripts/run_arc12_filename_holdout.py",
    "src/arc123/adapters/arc12.py",
    "src/arc123/compatibility.py",
    "src/arc123/contracts.py",
    "src/arc123/controller.py",
    "src/arc123/hypotheses.py",
    "src/arc123/model.py",
    "src/arc123/perceptions.py",
    "src/arc123/relational.py",
    "src/arc123/theory.py",
    "src/arc123/traces.py",
)
P0040_ANSWER_SOURCE_COMMIT = "c3842b7d28fb2829b79ec815a99b1bc39912a189"

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0041UniformFrameSizeFillTransferTests(unittest.TestCase):
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

    def test_p0041_retains_complete_final_transfer_artifacts(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(packet["implementation_commit"], packet["frozen_controller"]["commit"])
        self.assertEqual(summary["attempt_count"], 38)
        self.assertEqual(len(tasks), 38)
        self.assertEqual(summary["exact_solve_count"], 1)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 1, "arc2": 0})
        self.assertEqual(summary["complete_wrong_count"], 37)
        self.assertEqual(summary["training_exact_count"], 1)
        self.assertEqual(summary["fallback_count"], 37)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(packet["cohort_import"]["task_count"], 38)
        self.assertEqual(packet["cohort_import"]["per_benchmark_task_count"], 19)
        self.assertIn("Exact post-answer solves: `1/38`", readme)
        self.assertIn(
            "uniform_frame_size_fill",
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
        for raw_path in LIVE_ANSWER_SOURCE_FILES:
            self.assertEqual(
                self._pinned_bytes(packet["implementation_commit"], raw_path),
                self._pinned_bytes(P0040_ANSWER_SOURCE_COMMIT, raw_path),
            )
        for contract_name in ("synthetic_contract", "visual_contract"):
            contract = packet[contract_name]
            self.assertEqual(
                hashlib.sha256(
                    self._pinned_bytes(packet["implementation_commit"], contract["test_path"])
                ).hexdigest(),
                contract["test_sha256"],
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
        self.assertEqual(selected[("arc1", "94f9d214")], EXPECTED_HYPOTHESIS)
        self.assertEqual(
            sum(
                "uniform_frame_size_fill" in entry["selected_hypothesis"]
                for entry in summary["attempts"]
            ),
            0,
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
            self.assertNotIn("...", diagram)
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

        solve_diagram = (
            REPORT_ROOT / "arc1" / "94f9d214" / "corpus_callosum.svg"
        ).read_text(encoding="utf-8")
        self.assertIn("bilateral-panel merge", solve_diagram)


if __name__ == "__main__":
    unittest.main()
