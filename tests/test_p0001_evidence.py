from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKETS = (
    (
        REPOSITORY_ROOT / "research" / "packets" / "P0001_ARC12_TINY_REDISCOVERY.json",
        REPOSITORY_ROOT / "reports" / "P0001_arc12_tiny_rediscovery",
    ),
    (
        REPOSITORY_ROOT / "research" / "packets" / "P0002_ARC12_INITIAL_20.json",
        REPOSITORY_ROOT / "reports" / "P0002_arc12_initial_20",
    ),
    (
        REPOSITORY_ROOT
        / "research"
        / "packets"
        / "P0003_ARC12_CURATED_20_TILE_TRANSFER.json",
        REPOSITORY_ROOT / "reports" / "P0003_arc12_curated_20_tile_transfer",
    ),
)
COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_COHORT_IMPORT_001.json"


class PacketEvidenceTests(unittest.TestCase):
    def test_every_preregistered_attempt_has_complete_yes_or_no_vv_evidence(self) -> None:
        for packet_path, report_root in PACKETS:
            with self.subTest(packet=packet_path.name):
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                summary = json.loads((report_root / "receipt.json").read_text(encoding="utf-8"))
                self.assertEqual(summary["packet_id"], packet["packet_id"])
                self.assertEqual(summary["attempt_count"], len(packet["tasks"]))
                self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
                self.assertEqual(
                    {(entry["benchmark"], entry["task_id"]) for entry in summary["attempts"]},
                    {(entry["benchmark"], entry["task_id"]) for entry in packet["tasks"]},
                )
                for task in packet["tasks"]:
                    report_directory = report_root / task["benchmark"] / task["task_id"]
                    receipt = json.loads((report_directory / "receipt.json").read_text(encoding="utf-8"))
                    report = (report_directory / "REPORT.md").read_text(encoding="utf-8")
                    self.assertIsInstance(receipt["all_cells_match"], bool)
                    self.assertGreater(receipt["compared_position_count"], 0)
                    self.assertIsInstance(receipt["test_cases"], list)
                    self.assertTrue(receipt["test_cases"])
                    self.assertTrue(
                        all(isinstance(case["prediction"], list) for case in receipt["test_cases"])
                    )
                    self.assertEqual(receipt["controller_oracle_boundary_scan"], "pass")
                    self.assertTrue(
                        all(value is False for value in receipt["agent_input_contract"].values())
                    )
                    self.assertIn("## Outcome: YES" if receipt["all_cells_match"] else "## Outcome: NO", report)
                    self.assertTrue((report_directory / "learning_trace.json").is_file())
                    diagram = (report_directory / "corpus_callosum.svg").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', diagram)
                    self.assertEqual(diagram.count("<path "), 4)
                    self.assertIn("Compatibility core", diagram)
                    self.assertIn("UNKNOWN ≠ IMPOSSIBLE", diagram)
                    self.assertIn("Observable controller path", diagram)
                    if receipt["used_fallback"]:
                        self.assertIn("identity fallback", diagram)
                        self.assertNotIn("fallback_identity_complete_grid", diagram)

    def test_p0002_is_a_ten_by_ten_filename_only_selection(self) -> None:
        packet_path, _ = PACKETS[1]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))["curated_60"]["task_ids"]
        selection = packet["selection_protocol"]

        self.assertEqual(len(packet["tasks"]), 20)
        self.assertEqual(selection["allowed_inputs"], ["benchmark", "split", "task_id"])
        self.assertIn("held-out test output", selection["forbidden_inputs"])
        for benchmark in ("arc1", "arc2"):
            selected = [task for task in packet["tasks"] if task["benchmark"] == benchmark]
            self.assertEqual(len(selected), 10)
            expected = sorted(
                cohort[benchmark],
                key=lambda task: hashlib.sha256(
                    (
                        f"{selection['salt']}:{benchmark}:{task['split']}:"
                        f"{task['task_id']}"
                    ).encode("utf-8")
                ).hexdigest(),
            )[:10]
            self.assertEqual(
                [(task["split"], task["task_id"]) for task in selected],
                [(task["split"], task["task_id"]) for task in expected],
            )

    def test_p0003_excludes_prior_packets_and_recomputes_its_filename_rank(self) -> None:
        p0001 = json.loads(PACKETS[0][0].read_text(encoding="utf-8"))
        p0002 = json.loads(PACKETS[1][0].read_text(encoding="utf-8"))
        p0003 = json.loads(PACKETS[2][0].read_text(encoding="utf-8"))
        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))["curated_60"]["task_ids"]
        selection = p0003["selection_protocol"]
        excluded = {
            (task["benchmark"], task["split"], task["task_id"])
            for task in [*p0001["tasks"], *p0002["tasks"]]
        }

        self.assertEqual(len(p0003["tasks"]), 20)
        self.assertTrue(
            excluded.isdisjoint(
                {(task["benchmark"], task["split"], task["task_id"]) for task in p0003["tasks"]}
            )
        )
        for benchmark in ("arc1", "arc2"):
            selected = [task for task in p0003["tasks"] if task["benchmark"] == benchmark]
            eligible = [
                task
                for task in cohort[benchmark]
                if (benchmark, task["split"], task["task_id"]) not in excluded
            ]
            expected = sorted(
                eligible,
                key=lambda task: hashlib.sha256(
                    (
                        f"{selection['salt']}:{benchmark}:{task['split']}:"
                        f"{task['task_id']}"
                    ).encode("utf-8")
                ).hexdigest(),
            )[:10]
            self.assertEqual(
                [(task["split"], task["task_id"]) for task in selected],
                [(task["split"], task["task_id"]) for task in expected],
            )


if __name__ == "__main__":
    unittest.main()
