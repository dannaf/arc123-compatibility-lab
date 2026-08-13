from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import run_arc12_tiny_rediscovery as packet_runner


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
    (
        REPOSITORY_ROOT
        / "research"
        / "packets"
        / "P0005_ARC12_PERSISTENT_THEORY_CURATED_60.json",
        REPOSITORY_ROOT / "reports" / "P0005_arc12_persistent_theory_curated_60",
    ),
    (
        REPOSITORY_ROOT
        / "research"
        / "packets"
        / "P0006_ARC12_RESIDUAL_DIHEDRAL_TILE_CURATED_60.json",
        REPOSITORY_ROOT / "reports" / "P0006_arc12_residual_dihedral_tile_curated_60",
    ),
    (
        REPOSITORY_ROOT
        / "research"
        / "packets"
        / "P0011_ARC12_DIHEDRAL_COORDINATE_CURATED_60.json",
        REPOSITORY_ROOT / "reports" / "P0011_arc12_dihedral_coordinate_curated_60",
    ),
    (
        REPOSITORY_ROOT
        / "research"
        / "packets"
        / "P0012_ARC12_SELF_MASK_MACRO_STAMP_CURATED_60.json",
        REPOSITORY_ROOT / "reports" / "P0012_arc12_self_mask_macro_stamp_curated_60",
    ),
)
COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_COHORT_IMPORT_001.json"
P0011_PACKET = REPOSITORY_ROOT / "research" / "packets" / "P0011_ARC12_DIHEDRAL_COORDINATE_CURATED_60.json"
P0011_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0011_arc12_dihedral_coordinate_curated_60"
P0012_PACKET = REPOSITORY_ROOT / "research" / "packets" / "P0012_ARC12_SELF_MASK_MACRO_STAMP_CURATED_60.json"
P0012_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0012_arc12_self_mask_macro_stamp_curated_60"


class PacketEvidenceTests(unittest.TestCase):
    def test_each_packet_declares_its_own_safe_default_report_root(self) -> None:
        for packet_path, report_root in PACKETS:
            with self.subTest(packet=packet_path.name):
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                self.assertEqual(packet_runner._default_report_root(packet), report_root)
        with self.assertRaises(ValueError):
            packet_runner._default_report_root({"report_root": "../outside"})

    def test_every_preregistered_attempt_has_complete_yes_or_no_vv_evidence(self) -> None:
        for packet_path, report_root in PACKETS:
            with self.subTest(packet=packet_path.name):
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
                summary = json.loads((report_root / "receipt.json").read_text(encoding="utf-8"))
                tasks = packet_runner._packet_tasks(packet)
                self.assertEqual(summary["packet_id"], packet["packet_id"])
                self.assertEqual(summary["attempt_count"], len(tasks))
                self.assertEqual(summary["controller_oracle_boundary_scan"], "pass")
                self.assertEqual(
                    {(entry["benchmark"], entry["task_id"]) for entry in summary["attempts"]},
                    {(entry["benchmark"], entry["task_id"]) for entry in tasks},
                )
                for task in tasks:
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

    def test_p0005_freezes_the_persistent_theory_measurement_roster(self) -> None:
        packet_path, report_root = PACKETS[3]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        summary = json.loads((report_root / "receipt.json").read_text(encoding="utf-8"))
        tasks = packet_runner._packet_tasks(packet)

        self.assertEqual(packet["controller"]["implementation"], "persistent_partial_theory")
        self.assertEqual(len(tasks), 60)
        self.assertEqual(len([task for task in tasks if task["benchmark"] == "arc1"]), 30)
        self.assertEqual(len([task for task in tasks if task["benchmark"] == "arc2"]), 30)
        self.assertEqual(summary["exact_solve_count"], 1)
        self.assertEqual(summary["complete_wrong_count"], 59)
        self.assertEqual(summary["training_exact_count"], 1)
        self.assertEqual(summary["fallback_count"], 59)

    def test_p0006_retains_residual_directed_dihedral_transfer_evidence(self) -> None:
        packet_path, report_root = PACKETS[4]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        summary = json.loads((report_root / "receipt.json").read_text(encoding="utf-8"))
        tasks = packet_runner._packet_tasks(packet)

        self.assertIn("dihedral_tile", packet["controller"]["generic_operator_families"])
        self.assertEqual(len(tasks), 60)
        self.assertEqual(summary["exact_solve_count"], 4)
        self.assertEqual(summary["complete_wrong_count"], 56)
        exact = {
            (item["benchmark"], item["task_id"]): item["selected_hypothesis"]
            for item in summary["attempts"]
            if item["all_cells_match"]
        }
        self.assertEqual(
            set(exact),
            {
                ("arc1", "833dafe3"),
                ("arc1", "8be77c9e"),
                ("arc1", "a699fb00"),
                ("arc2", "00576224"),
            },
        )
        self.assertEqual(sum("dihedral_tile" in hypothesis for hypothesis in exact.values()), 3)
        dihedral_diagram = (
            report_root / "arc2" / "00576224" / "corpus_callosum.svg"
        ).read_text(encoding="utf-8")
        self.assertIn("dihedral macro-tile", dihedral_diagram)
        self.assertIn("UNKNOWN RESIDUAL", dihedral_diagram)

    def test_p0011_pins_its_unfrozen_baseline_and_does_not_rewrite_p0008(self) -> None:
        packet = json.loads(P0011_PACKET.read_text(encoding="utf-8"))
        report_root = P0011_REPORT_ROOT
        summary = json.loads((report_root / "receipt.json").read_text(encoding="utf-8"))
        tasks = packet_runner._packet_tasks(packet)

        self.assertEqual(len(tasks), 60)
        self.assertIn("dihedral_transform", packet["controller"]["generic_operator_families"])
        self.assertFalse(packet["external_mutation_allowed"])
        self.assertFalse(packet["benchmark_submission_allowed"])
        self.assertTrue(packet["acceptance"]["do_not_rewrite_p0008_frozen_measurement"])
        packet_runner._verify_packet_boundary(packet)
        packet_runner._verify_baseline_reference(packet)
        self.assertEqual(summary["exact_solve_count"], 4)
        self.assertEqual(summary["baseline_comparison"]["exact_solve_count"], 4)
        self.assertEqual(summary["baseline_comparison"]["exact_solve_delta"], 0)
        self.assertFalse(
            any(
                "dihedral_transform" in attempt["selected_hypothesis"]
                for attempt in summary["attempts"]
            )
        )
        readme = (report_root / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Pre-Registered Baseline Comparison", readme)
        self.assertIn("Exact-solve delta: `0`", readme)

    def test_p0012_retains_macro_stamp_gain_without_rewriting_p0008(self) -> None:
        packet = json.loads(P0012_PACKET.read_text(encoding="utf-8"))
        summary = json.loads((P0012_REPORT_ROOT / "receipt.json").read_text(encoding="utf-8"))
        tasks = packet_runner._packet_tasks(packet)

        self.assertEqual(len(tasks), 60)
        self.assertIn("self_mask_macro_stamp", packet["controller"]["generic_operator_families"])
        self.assertFalse(packet["external_mutation_allowed"])
        self.assertFalse(packet["benchmark_submission_allowed"])
        self.assertTrue(packet["acceptance"]["do_not_rewrite_p0008_frozen_measurement"])
        packet_runner._verify_packet_boundary(packet)
        packet_runner._verify_baseline_reference(packet)
        self.assertEqual(summary["exact_solve_count"], 8)
        self.assertEqual(summary["baseline_comparison"]["exact_solve_count"], 4)
        self.assertEqual(summary["baseline_comparison"]["exact_solve_delta"], 4)
        exact = {
            (attempt["benchmark"], attempt["task_id"]): attempt["selected_hypothesis"]
            for attempt in summary["attempts"]
            if attempt["all_cells_match"]
        }
        macro_exact = {
            task: hypothesis
            for task, hypothesis in exact.items()
            if "self_mask_macro_stamp" in hypothesis
        }
        self.assertEqual(
            set(macro_exact),
            {
                ("arc1", "27f8ce4f"),
                ("arc1", "48f8583b"),
                ("arc2", "007bbfb7"),
                ("arc2", "8e2edd66"),
            },
        )
        self.assertIn("selector=most_frequent", macro_exact[("arc1", "27f8ce4f")])
        self.assertIn("selector=least_frequent", macro_exact[("arc1", "48f8583b")])
        self.assertIn("selector=nonzero", macro_exact[("arc2", "007bbfb7")])
        self.assertIn("selector=zero", macro_exact[("arc2", "8e2edd66")])
        readme = (P0012_REPORT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Pre-Registered Baseline Comparison", readme)
        self.assertIn("Exact-solve delta: `4`", readme)

    def test_persistent_theory_packet_traces_do_not_receive_task_identifiers(self) -> None:
        for packet_path, report_root in PACKETS[3:]:
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            for task in packet_runner._packet_tasks(packet):
                trace_path = report_root / task["benchmark"] / task["task_id"] / "learning_trace.json"
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                self.assertNotIn(task["task_id"], trace["episode_id"])

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
