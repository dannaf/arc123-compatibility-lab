from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0017_ARC12_SELF_CONTAINED_SUBSET_CROP_DEVELOPMENT_40.json"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0017_arc12_self_contained_subset_crop_development_40"
BASELINE_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0016_arc12_development_baseline_40"

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0017SelfContainedSubsetCropDevelopmentTests(unittest.TestCase):
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

    def test_p0017_is_complete_reproducible_and_has_zero_baseline_delta(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        baseline = json.loads((BASELINE_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(summary["attempt_count"], 40)
        self.assertEqual(len(tasks), 40)
        self.assertEqual(summary["exact_solve_count"], baseline["exact_solve_count"])
        self.assertEqual(summary["exact_solve_count"], 0)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], baseline["exact_solve_count_by_benchmark"])
        self.assertEqual(summary["complete_wrong_count"], baseline["complete_wrong_count"])
        self.assertEqual(summary["complete_wrong_count"], 40)
        self.assertEqual(summary["training_exact_count"], baseline["training_exact_count"])
        self.assertEqual(summary["training_exact_count"], 0)
        self.assertEqual(summary["fallback_count"], baseline["fallback_count"])
        self.assertEqual(summary["fallback_count"], 40)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(summary["frozen_controller"], {
            "commit": packet["frozen_controller"]["commit"],
            "source_files": packet["frozen_controller"]["source_files"],
        })
        self.assertEqual(packet["baseline_reference"]["exact_solve_count"], baseline["exact_solve_count"])
        self.assertTrue(all(value is False for value in packet["offline_diagnostic_provenance"]["live_controller_boundary"].values()))
        self.assertIn("self_contained_subset_crop", packet["frozen_controller"]["generic_operator_families"])
        self.assertIn("Exact post-answer solves: `0/40`", readme)
        self.assertFalse(any("self_contained_subset_crop" in entry["selected_hypothesis"] for entry in summary["attempts"]))
        self._assert_frozen_controller_bytes(packet)

        baseline_attempts = {
            (entry["benchmark"], entry["task_id"]): entry for entry in baseline["attempts"]
        }
        self.assertEqual(
            {(entry["benchmark"], entry["task_id"]) for entry in summary["attempts"]},
            set(baseline_attempts),
        )
        for task in tasks:
            report_directory = REPORT_ROOT / task["benchmark"] / task["task_id"]
            receipt = json.loads((report_directory / "receipt.json").read_text(encoding="utf-8"))
            baseline_receipt = json.loads(
                (BASELINE_REPORT_ROOT / task["benchmark"] / task["task_id"] / "receipt.json").read_text(
                    encoding="utf-8"
                )
            )
            report = (report_directory / "REPORT.md").read_text(encoding="utf-8")
            trace = json.loads((report_directory / "learning_trace.json").read_text(encoding="utf-8"))
            diagram = (report_directory / "corpus_callosum.svg").read_text(encoding="utf-8")

            self.assertEqual(receipt["all_cells_match"], baseline_attempts[(task["benchmark"], task["task_id"])]["all_cells_match"])
            self.assertEqual(receipt["test_cases"], baseline_receipt["test_cases"])
            self.assertEqual(receipt["frozen_controller"], summary["frozen_controller"])
            self.assertEqual(receipt["controller_oracle_boundary_scan"], "pass")
            self.assertTrue(all(value is False for value in receipt["agent_input_contract"].values()))
            self.assertIn("Expected output (post-answer only)", report)
            self.assertTrue(trace["events"])
            self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', diagram)
            self.assertIn("Committed output", diagram)
            for artifact in receipt["trace_artifacts"].values():
                artifact_path = report_directory / artifact["path"]
                self.assertEqual(hashlib.sha256(artifact_path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
