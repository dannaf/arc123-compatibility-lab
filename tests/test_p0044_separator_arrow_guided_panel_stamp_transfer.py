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
    / "P0044_ARC12_SEPARATOR_ARROW_GUIDED_PANEL_STAMP_MIXED_PARTITION_TRANSFER_40.json"
)
P0043_PACKET_PATH = (
    REPOSITORY_ROOT
    / "research"
    / "packets"
    / "P0043_ARC12_SEPARATOR_ARROW_GUIDED_PANEL_STAMP_DEVELOPMENT_40.json"
)
P0043_COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_MIXED_PARTITION_DEVELOPMENT_011.json"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0044_arc12_separator_arrow_guided_panel_stamp_mixed_partition_transfer_40"
EXPECTED_SOLVES = {
    ("arc1", "281123b4"),
    ("arc2", "0c786b71"),
    ("arc2", "bc4146bd"),
}

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0044SeparatorArrowGuidedPanelStampTransferTests(unittest.TestCase):
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

    def test_p0044_retains_complete_fresh_mixed_partition_transfer_artifacts(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        p0043_packet = json.loads(P0043_PACKET_PATH.read_text(encoding="utf-8"))
        p0043_cohort = json.loads(P0043_COHORT_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(packet["implementation_commit"], packet["frozen_controller"]["commit"])
        self.assertEqual(packet["implementation_commit"], p0043_packet["implementation_commit"])
        self.assertEqual(
            packet["frozen_controller"]["generic_operator_families"],
            p0043_packet["frozen_controller"]["generic_operator_families"],
        )
        self.assertEqual(summary["attempt_count"], 40)
        self.assertEqual(len(tasks), 40)
        self.assertEqual(summary["exact_solve_count"], 3)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 1, "arc2": 2})
        self.assertEqual(summary["complete_wrong_count"], 37)
        self.assertEqual(summary["training_exact_count"], 3)
        self.assertEqual(summary["fallback_count"], 37)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertIn("fresh transfer measurement", packet["claim_boundary"])
        self.assertIn("non-comparable", packet["claim_boundary"])
        self.assertIn("Exact post-answer solves: `3/40`", readme)
        self.assertTrue(
            all(
                value is False
                for value in packet["offline_diagnostic_provenance"][
                    "live_controller_boundary"
                ].values()
            )
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
        self.assertIn("separated_panel_cellwise_combine", selected[("arc1", "281123b4")])
        self.assertIn("dihedral_tile", selected[("arc2", "0c786b71")])
        self.assertIn("dihedral_tile", selected[("arc2", "bc4146bd")])
        self.assertEqual(
            sum(
                "separator_arrow_guided_panel_stamp" in entry["selected_hypothesis"]
                for entry in summary["attempts"]
            ),
            0,
        )

        p0043_task_ids = {
            record["task_id"]
            for records in p0043_cohort["mixed_partition_development_40_p0042"][
                "tasks"
            ].values()
            for record in records
        }
        p0044_task_ids = {task["task_id"] for task in tasks}
        self.assertFalse(p0043_task_ids & p0044_task_ids)

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

        panel_diagram = (
            REPORT_ROOT / "arc1" / "281123b4" / "corpus_callosum.svg"
        ).read_text(encoding="utf-8")
        self.assertIn("separated-panel merge", panel_diagram)


if __name__ == "__main__":
    unittest.main()
