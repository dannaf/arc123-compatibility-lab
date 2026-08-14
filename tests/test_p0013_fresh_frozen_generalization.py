from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0013_ARC12_FRESH_FILENAME_FROZEN_50.json"
COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_FILENAME_HOLDOUT_001.json"
REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0013_arc12_fresh_filename_frozen_50"

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_filename_holdout as packet_runner


class P0013FreshFrozenGeneralizationTests(unittest.TestCase):
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

    def test_p0013_is_complete_reproducible_and_negative(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        summary = json.loads((REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        readme = (REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        tasks = packet_runner._task_records(packet)

        self.assertEqual(summary["packet_id"], packet["packet_id"])
        self.assertEqual(summary["attempt_count"], 50)
        self.assertEqual(len(tasks), 50)
        self.assertEqual(summary["exact_solve_count"], 0)
        self.assertEqual(summary["exact_solve_count_by_benchmark"], {"arc1": 0, "arc2": 0})
        self.assertEqual(summary["complete_wrong_count"], 50)
        self.assertEqual(summary["training_exact_count"], 0)
        self.assertEqual(summary["fallback_count"], 50)
        self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
        self.assertEqual(summary["frozen_controller"], {
            "commit": packet["frozen_controller"]["commit"],
            "source_files": packet["frozen_controller"]["source_files"],
        })
        self._assert_frozen_controller_bytes(packet)
        self.assertIn("Exact post-answer solves: `0/50`", readme)

        frozen = cohort["frozen_filename_only_50"]
        self.assertEqual(frozen["task_count"], 50)
        self.assertEqual(len(frozen["tasks"]["arc1"]), 25)
        self.assertEqual(len(frozen["tasks"]["arc2"]), 25)
        for benchmark in ("arc1", "arc2"):
            records = frozen["tasks"][benchmark]
            self.assertEqual(sum(record["split"] == "evaluation" for record in records), 12)
            self.assertEqual(sum(record["split"] == "training" for record in records), 13)
            self.assertTrue(all(len(record["selection_hash"]) == 64 for record in records))
            self.assertTrue(all(len(record["source_sha256"]) == 64 for record in records))
        self.assertFalse(
            {record["task_id"] for record in frozen["tasks"]["arc1"]}
            & {record["task_id"] for record in frozen["tasks"]["arc2"]}
        )

        self.assertEqual(
            {(entry["benchmark"], entry["task_id"]) for entry in summary["attempts"]},
            {(task["benchmark"], task["task_id"]) for task in tasks},
        )
        for task in tasks:
            report_directory = REPORT_ROOT / task["benchmark"] / task["task_id"]
            receipt = json.loads((report_directory / "receipt.json").read_text(encoding="utf-8"))
            report = (report_directory / "REPORT.md").read_text(encoding="utf-8")
            trace = json.loads((report_directory / "learning_trace.json").read_text(encoding="utf-8"))
            diagram = (report_directory / "corpus_callosum.svg").read_text(encoding="utf-8")

            self.assertFalse(receipt["all_cells_match"])
            self.assertFalse(receipt["training_exact"])
            self.assertTrue(receipt["used_fallback"])
            self.assertEqual(receipt["selected_hypothesis"], "fallback_identity_complete_grid")
            self.assertEqual(receipt["frozen_controller"], summary["frozen_controller"])
            self.assertEqual(receipt["controller_oracle_boundary_scan"], "pass")
            self.assertTrue(all(value is False for value in receipt["agent_input_contract"].values()))
            self.assertNotIn(task["task_id"], trace["episode_id"])
            self.assertIn("## Outcome: NO — TEST CELLS DO NOT ALL MATCH", report)
            self.assertIn("Expected output (post-answer only)", report)
            self.assertTrue(receipt["test_cases"])
            self.assertTrue(
                all(isinstance(test_case["prediction"], list) for test_case in receipt["test_cases"])
            )
            self.assertTrue(trace["events"])
            self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', diagram)
            self.assertIn("Committed output", diagram)
            self.assertIn("identity fallback", diagram)

            for artifact in receipt["trace_artifacts"].values():
                artifact_path = report_directory / artifact["path"]
                self.assertEqual(hashlib.sha256(artifact_path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
