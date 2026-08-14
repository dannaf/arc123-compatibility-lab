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
    / "P0038_ARC12_CROSS_SEPARATOR_REFLECTION_TRAINING_TRANSFER_50.json"
)
P0037_PACKET_PATH = (
    REPOSITORY_ROOT
    / "research"
    / "packets"
    / "P0037_ARC12_CROSS_SEPARATOR_REFLECTION_DEVELOPMENT_40.json"
)
P0037_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0037_arc12_cross_separator_reflection_development_40"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0038_arc12_cross_separator_reflection_training_transfer_50"
EXPECTED_SOLVES = {("arc1", "d511f180")}

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0038CrossSeparatorReflectionTransferTests(unittest.TestCase):
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

    def test_p0038_retains_negative_transfer_and_complete_vv_artifacts(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        p0037_packet = json.loads(P0037_PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        p0037_summary = json.loads((P0037_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(packet["implementation_commit"], packet["frozen_controller"]["commit"])
        self.assertEqual(summary["attempt_count"], 50)
        self.assertEqual(len(tasks), 50)
        self.assertEqual(summary["exact_solve_count"], 1)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 1, "arc2": 0})
        self.assertEqual(summary["complete_wrong_count"], 49)
        self.assertEqual(summary["training_exact_count"], 1)
        self.assertEqual(summary["fallback_count"], 49)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(packet["cohort_import"]["task_count"], 50)
        self.assertEqual(packet["cohort_import"]["per_benchmark_task_count"], 25)
        self.assertEqual(packet["implementation_reference"]["exact_solve_count"], 3)
        self.assertEqual(p0037_summary["exact_solve_count"], 3)
        self.assertEqual(p0037_summary["attempt_count"], 40)
        self.assertIn("Exact post-answer solves: `1/50`", readme)
        self.assertIn(
            "cross_separator_quadrant_reflection_stamp",
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
            p0037_packet["frozen_controller"]["commit"],
        )
        common_source_files = set(packet["frozen_controller"]["source_files"]) & set(
            p0037_packet["frozen_controller"]["source_files"]
        )
        for raw_path in common_source_files:
            self.assertEqual(
                packet["frozen_controller"]["source_files"][raw_path],
                p0037_packet["frozen_controller"]["source_files"][raw_path],
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
        self.assertEqual(
            {
                entry["selected_hypothesis"].split("(", 1)[0]
                for entry in summary["attempts"]
                if entry["all_cells_match"]
            },
            {"recolor"},
        )
        self.assertFalse(
            any(
                "cross_separator_quadrant_reflection_stamp" in entry["selected_hypothesis"]
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
