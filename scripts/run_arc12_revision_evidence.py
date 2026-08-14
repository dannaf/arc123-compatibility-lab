#!/usr/bin/env python3
"""Run or verify the source-pinned ARC12 conditional-revision evidence packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.traces import render_corpus_callosum_svg, render_trace_markdown


PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0007_ARC12_CONDITIONAL_REVISION_10.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): _sha256(path)
        for path in sorted(root.glob("**/*"))
        if path.is_file()
    }


def _git_output(source_root: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _verify_clean_source(source_root: Path, expected_commit: str) -> None:
    if _git_output(source_root, ["rev-parse", "HEAD"]) != expected_commit:
        raise ValueError(f"source revision does not match pin: {source_root}")
    if _git_output(source_root, ["status", "--porcelain"]):
        raise ValueError(f"source must remain clean and read-only: {source_root}")


def _controller_boundary_holds() -> bool:
    source = (REPOSITORY_ROOT / "src" / "arc123" / "controller.py").read_text(
        encoding="utf-8"
    )
    forbidden_tokens = ("_test_targets", "post_answer_validate", "expected_output", "task_id")
    return not any(token in source for token in forbidden_tokens)


def _packet_tasks(packet: Mapping[str, Any]) -> list[dict[str, str]]:
    reference = packet.get("cohort_reference")
    if not isinstance(reference, Mapping):
        raise ValueError("packet must declare a cohort_reference")
    raw_path = reference.get("path")
    expected_sha256 = reference.get("sha256")
    if not isinstance(raw_path, str) or not isinstance(expected_sha256, str):
        raise ValueError("cohort_reference must declare a path and sha256")
    relative_path = Path(raw_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("cohort reference must remain inside the repository")
    cohort_path = REPOSITORY_ROOT / relative_path
    if _sha256(cohort_path) != expected_sha256:
        raise ValueError("cohort reference does not match its immutable sha256")
    cohort = _load_json(cohort_path)
    raw_tasks = cohort.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("revision cohort must contain task records")
    expected_count = int(reference.get("task_count", 0))
    if len(raw_tasks) != expected_count:
        raise ValueError("revision cohort task count does not match packet")
    tasks: list[dict[str, str]] = []
    for task in raw_tasks:
        if not isinstance(task, Mapping):
            raise ValueError("revision cohort contains a malformed task")
        benchmark = task.get("benchmark")
        split = task.get("split")
        task_id = task.get("task_id")
        if not all(isinstance(value, str) and value for value in (benchmark, split, task_id)):
            raise ValueError("revision cohort task lacks benchmark, split, or task_id")
        tasks.append({"benchmark": benchmark, "split": split, "task_id": task_id})
    return tasks


def _controller_from_configuration(configuration: Mapping[str, Any]) -> IterativeHypothesisLearner:
    if configuration.get("implementation") != "persistent_partial_theory":
        raise ValueError("P0007 requires the persistent partial-theory controller")
    families = configuration.get("generic_operator_families")
    if not isinstance(families, list) or not all(isinstance(item, str) for item in families):
        raise ValueError("controller configuration must list generic operator families")
    return IterativeHypothesisLearner(
        candidate_limit=int(configuration["candidate_limit"]),
        beam_width=int(configuration["beam_width"]),
        max_revisions=int(configuration["max_revisions"]),
        revision_enabled=bool(configuration.get("revision_enabled", True)),
        operator_families=tuple(families),
    )


def _causal_assessment(result: Mapping[str, Any], all_cells_match: bool) -> dict[str, Any]:
    trace = result["trace"]
    events = trace.get("events", [])
    actions = [str(event.get("action")) for event in events if isinstance(event, Mapping)]
    final_theory = result.get("final_theory") or {}
    rules = final_theory.get("rules", []) if isinstance(final_theory, Mapping) else []
    operations = [
        str(rule.get("operation")) for rule in rules if isinstance(rule, Mapping)
    ]
    residual_operations = {
        "component_property_recolor",
        "component_property_erase",
        "marker_shape_target_recolor",
        "erase_color_to_background",
    }
    generic_families: list[str] = []
    if "marker_shape_target_recolor" in operations:
        generic_families.append("marker_shape_target_recolor")
    if "component_property_recolor" in operations:
        generic_families.append("component_property_recolor")
    if "component_property_erase" in operations:
        generic_families.append("component_property_erase")
    if any(
        isinstance(rule, Mapping)
        and rule.get("operation") == "full_operator"
        and rule.get("parameters", {}).get("operator") == "row_span_fill"
        and rule.get("parameters", {}).get("selection") == "global_minimum"
        for rule in rules
    ):
        generic_families.append("row_span_minimum")
    counterexample_seen = "FIND_COUNTEREXAMPLE" in actions
    extra_demo_seen = "CHOOSE_NEXT_DEMO" in actions
    composition_seen = "COMPOSE_RULE" in actions
    promotion_seen = "PROMOTE_CONSTRAINT" in actions
    parameter_revision_seen = "BIND_PARAMETER" in actions
    multi_rule_residual = sum(operation in residual_operations for operation in operations) >= 2
    rule_revision_seen = parameter_revision_seen or multi_rule_residual
    return {
        "all_cells_match": all_cells_match,
        "counterexample_seen": counterexample_seen,
        "visible_additional_demo_seen": extra_demo_seen,
        "composition_seen": composition_seen,
        "promotion_seen": promotion_seen,
        "parameter_revision_seen": parameter_revision_seen,
        "multi_rule_residual": multi_rule_residual,
        "selected_rule_operations": operations,
        "generic_families": generic_families,
        "accepted": bool(
            all_cells_match
            and result["training_exact"]
            and not result["used_fallback"]
            and counterexample_seen
            and extra_demo_seen
            and composition_seen
            and promotion_seen
            and rule_revision_seen
        ),
    }


def _run_configuration(
    configuration: Mapping[str, Any], environment: ARC12InteractiveEnv, packet_id: str, name: str
) -> tuple[Any, list[dict[str, Any]]]:
    controller = _controller_from_configuration(configuration)
    result = controller.solve(environment, f"{packet_id}:{name}:anonymous-live-evidence")
    validation = environment.post_answer_validate(result.predictions)
    return result, validation


def _report_text(receipt: Mapping[str, Any], trace: Mapping[str, Any]) -> str:
    outcome = "YES — ALL TEST CELLS MATCH" if receipt["all_cells_match"] else "NO — TEST CELLS DO NOT ALL MATCH"
    causal = "YES" if receipt["causal_trace"]["accepted"] else "NO"
    lines = [
        f"# {receipt['benchmark'].upper()} `{receipt['task_id']}` P0007 Brain Surgery Report",
        "",
        f"## Outcome: {outcome}",
        "",
        f"- **Compared positions:** {receipt['compared_position_count']}",
        f"- **Mismatched cells:** {receipt['mismatched_cell_count']}",
        f"- **Training compatibility:** `{receipt['training_exact']}`",
        f"- **Fallback used:** `{receipt['used_fallback']}`",
        f"- **Causal trace acceptance:** `{causal}`",
        f"- **Selected hypothesis:** `{receipt['selected_hypothesis']}`",
        f"- **Source commit:** `{receipt['source_commit']}`",
        "",
        "## Causal Ablations",
        "",
        "| Configuration | Exact all-cell result | Training exact | Fallback | Selected hypothesis |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, ablation in receipt["ablations"].items():
        lines.append(
            f"| `{name}` | `{ablation['all_cells_match']}` | `{ablation['training_exact']}` | "
            f"`{ablation['used_fallback']}` | `{ablation['selected_hypothesis']}` |"
        )
    causal_trace = receipt["causal_trace"]
    lines.extend(
        [
            "",
            "## Live-Agent Boundary",
            "",
            "The controller receives only visible training input/output examples and test inputs. It receives no task ID, offline audit label, GT feature record, GT solver, historical decomposition, or held-out output before committing a complete grid. The expected output appears only in the post-answer V&V section.",
            "",
            "## Corpus-Callosum Visualization",
            "",
            "![P0007 corpus-callosum trace](corpus_callosum.svg)",
            "",
            "- Full explicit event record: [`learning_trace.json`](learning_trace.json)",
            "- Full three-configuration record: [`ablations.json`](ablations.json)",
            "",
            "## Causal Trace Check",
            "",
            f"- **Counterexample observed:** `{causal_trace['counterexample_seen']}`",
            f"- **Additional visible demonstration selected:** `{causal_trace['visible_additional_demo_seen']}`",
            f"- **Composition recorded:** `{causal_trace['composition_seen']}`",
            f"- **Parameter or multi-rule revision:** `{causal_trace['parameter_revision_seen'] or causal_trace['multi_rule_residual']}`",
            f"- **Generic families in selected theory:** `{', '.join(causal_trace['generic_families']) or 'none'}`",
            "",
            "## Post-Answer V&V",
            "",
        ]
    )
    for test_case in receipt["test_cases"]:
        lines.extend(
            [
                f"### Test case {test_case['test_index'] + 1}",
                f"- **All cells match:** `{test_case['all_cells_match']}`",
                f"- **Mismatched cells:** `{test_case['mismatched_cell_count']}`",
                "- **Prediction:**",
                "```json",
                json.dumps(test_case["prediction"], ensure_ascii=False),
                "```",
                "- **Expected output (post-answer only):**",
                "```json",
                json.dumps(test_case["expected_output"], ensure_ascii=False),
                "```",
                "",
            ]
        )
    lines.extend([render_trace_markdown(trace).rstrip(), ""])
    return "\n".join(lines)


def _task_receipt(
    packet: Mapping[str, Any],
    task: Mapping[str, str],
    source_root: Path,
    report_directory: Path,
) -> dict[str, Any]:
    benchmark = task["benchmark"]
    task_id = task["task_id"]
    task_path = source_root / "arc_data" / benchmark / task["split"] / f"{task_id}.json"
    if not task_path.is_file():
        raise ValueError(f"source-pinned task does not exist: {task_path}")
    source_pin = packet["source_pins"][benchmark]
    environment = ARC12InteractiveEnv.from_task_payload(
        _load_json(task_path),
        provenance={
            "benchmark": benchmark,
            "task_id": task_id,
            "split": task["split"],
            "source_commit": source_pin["commit"],
            "source_task_url": (
                f"{source_pin['repository']}/blob/{source_pin['commit']}/"
                f"arc_data/{benchmark}/{task['split']}/{task_id}.json"
            ),
        },
    )
    full_result, full_validation = _run_configuration(
        packet["controller"], environment, str(packet["packet_id"]), "full"
    )
    all_cells_match = all(item["all_cells_match"] for item in full_validation)
    ablations: dict[str, Any] = {}
    for name, configuration in packet["ablations"].items():
        if not isinstance(configuration, Mapping):
            raise ValueError("packet ablation configuration must be an object")
        result, validation = _run_configuration(
            configuration, environment, str(packet["packet_id"]), name
        )
        ablations[name] = {
            "all_cells_match": all(item["all_cells_match"] for item in validation),
            "training_exact": result.training_exact,
            "used_fallback": result.used_fallback,
            "selected_hypothesis": result.selected_hypothesis,
            "mismatched_cell_count": sum(item["mismatched_cell_count"] for item in validation),
        }
    trace_path = report_directory / "learning_trace.json"
    diagram_path = report_directory / "corpus_callosum.svg"
    ablation_path = report_directory / "ablations.json"
    _write_json(trace_path, full_result.trace)
    render_corpus_callosum_svg(
        diagram_path,
        environment.test_inputs[0],
        full_result.predictions[0],
        full_result.selected_hypothesis,
        full_result.trace,
    )
    _write_json(ablation_path, ablations)
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "benchmark": benchmark,
        "task_id": task_id,
        "task_split": task["split"],
        "source_commit": source_pin["commit"],
        "source_task_url": environment.provenance_for_report()["source_task_url"],
        "agent_input_contract": {
            "task_id_passed_to_agent": False,
            "offline_audit_passed_to_agent": False,
            "gt_feature_contract_passed_to_agent": False,
            "gt_solver_imported_or_called": False,
            "held_out_outputs_passed_to_agent": False,
        },
        "controller_oracle_boundary_scan": "pass" if _controller_boundary_holds() else "fail",
        "selected_hypothesis": full_result.selected_hypothesis,
        "training_exact": full_result.training_exact,
        "used_fallback": full_result.used_fallback,
        "posterior_mass": full_result.posterior_mass,
        "all_cells_match": all_cells_match,
        "mismatched_cell_count": sum(item["mismatched_cell_count"] for item in full_validation),
        "compared_position_count": sum(item["compared_position_count"] for item in full_validation),
        "test_cases": full_validation,
        "causal_trace": _causal_assessment(
            {
                "trace": full_result.trace,
                "final_theory": full_result.final_theory,
                "training_exact": full_result.training_exact,
                "used_fallback": full_result.used_fallback,
            },
            all_cells_match,
        ),
        "ablations": ablations,
        "trace_artifacts": {
            "learning_trace": {"path": "learning_trace.json", "sha256": _sha256(trace_path)},
            "corpus_callosum": {"path": "corpus_callosum.svg", "sha256": _sha256(diagram_path)},
            "ablations": {"path": "ablations.json", "sha256": _sha256(ablation_path)},
        },
    }
    _write_json(report_directory / "receipt.json", receipt)
    report_path = report_directory / "REPORT.md"
    report_path.write_text(_report_text(receipt, full_result.trace), encoding="utf-8")
    receipt["trace_artifacts"]["report"] = {"path": "REPORT.md", "sha256": _sha256(report_path)}
    _write_json(report_directory / "receipt.json", receipt)
    return receipt


def run_packet(
    arc1_source: Path,
    arc2_source: Path,
    report_root: Path,
    packet_path: Path = PACKET_PATH,
) -> dict[str, Any]:
    packet = _load_json(packet_path)
    if not _controller_boundary_holds():
        raise ValueError("controller source violates the live-input boundary")
    source_roots = {"arc1": arc1_source, "arc2": arc2_source}
    for benchmark, source_root in source_roots.items():
        _verify_clean_source(source_root, str(packet["source_pins"][benchmark]["commit"]))
    receipts = [
        _task_receipt(
            packet,
            task,
            source_roots[task["benchmark"]],
            report_root / task["benchmark"] / task["task_id"],
        )
        for task in _packet_tasks(packet)
    ]
    exact_receipts = [receipt for receipt in receipts if receipt["all_cells_match"]]
    full_exact = len(exact_receipts)
    ablation_exact = {
        name: sum(receipt["ablations"][name]["all_cells_match"] for receipt in receipts)
        for name in packet["ablations"]
    }
    generic_families = sorted(
        {
            family
            for receipt in exact_receipts
            for family in receipt["causal_trace"]["generic_families"]
        }
    )
    acceptance = packet["frozen_generalization_gate"]
    minimum_advantage = int(acceptance["minimum_ablation_advantage"])
    frozen_gate_passed = (
        full_exact >= int(acceptance["minimum_exact_count"])
        and len(generic_families) >= int(acceptance["minimum_distinct_generic_families"])
        and all(full_exact - count >= minimum_advantage for count in ablation_exact.values())
    )
    summary = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "claim_boundary": packet["claim_boundary"],
        "controller_oracle_boundary_scan": "pass",
        "attempt_count": len(receipts),
        "exact_solve_count": full_exact,
        "complete_wrong_count": len(receipts) - full_exact,
        "causal_acceptance_count": sum(
            receipt["causal_trace"]["accepted"] for receipt in receipts
        ),
        "generic_families_in_exact_results": generic_families,
        "ablation_exact_counts": ablation_exact,
        "frozen_generalization_gate": {
            "passed": frozen_gate_passed,
            "minimum_exact_count": int(acceptance["minimum_exact_count"]),
            "minimum_distinct_generic_families": int(
                acceptance["minimum_distinct_generic_families"]
            ),
            "minimum_ablation_advantage": minimum_advantage,
        },
        "attempts": [
            {
                "benchmark": receipt["benchmark"],
                "task_id": receipt["task_id"],
                "all_cells_match": receipt["all_cells_match"],
                "causal_trace_accepted": receipt["causal_trace"]["accepted"],
                "selected_hypothesis": receipt["selected_hypothesis"],
                "ablations": receipt["ablations"],
            }
            for receipt in receipts
        ],
    }
    _write_json(report_root / "receipt.json", summary)
    lines = [
        str(packet["report_title"]),
        "",
        f"- Attempts: `{summary['attempt_count']}`",
        f"- Exact post-answer solves: `{summary['exact_solve_count']}/{summary['attempt_count']}`",
        f"- Causal-trace accepted exact solves: `{summary['causal_acceptance_count']}`",
        f"- No-revision exact solves: `{ablation_exact['no_revision']}`",
        f"- No-new-residual-family exact solves: `{ablation_exact['no_new_residual_family']}`",
        f"- Frozen 25+25 gate: `{'PASS' if frozen_gate_passed else 'NOT YET'}`",
        "",
        "| Benchmark | Task | Full result | Causal trace | No revision | No new residual family | Report |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for receipt in receipts:
        report = f"{receipt['benchmark']}/{receipt['task_id']}/REPORT.md"
        lines.append(
            f"| {receipt['benchmark'].upper()} | `{receipt['task_id']}` | "
            f"{'YES' if receipt['all_cells_match'] else 'NO'} | "
            f"{'YES' if receipt['causal_trace']['accepted'] else 'NO'} | "
            f"{'YES' if receipt['ablations']['no_revision']['all_cells_match'] else 'NO'} | "
            f"{'YES' if receipt['ablations']['no_new_residual_family']['all_cells_match'] else 'NO'} | "
            f"[brain surgery]({report}) |"
        )
    lines.extend(
        [
            "",
            "Every task is a committed complete prediction followed by post-answer V&V. A NO remains a first-class retained failure; the selected offline category is never a live agent input.",
            "",
        ]
    )
    (report_root / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--run", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--arc1-source", required=True, type=Path)
    parser.add_argument("--arc2-source", required=True, type=Path)
    parser.add_argument("--packet", type=Path, default=PACKET_PATH)
    parser.add_argument("--report-root", type=Path)
    arguments = parser.parse_args()
    packet = _load_json(arguments.packet)
    report_root = arguments.report_root or REPOSITORY_ROOT / str(packet["report_root"])
    if arguments.run:
        summary = run_packet(
            arguments.arc1_source, arguments.arc2_source, report_root, arguments.packet
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    with tempfile.TemporaryDirectory() as temporary_directory:
        reproduced_root = Path(temporary_directory)
        reproduced = run_packet(
            arguments.arc1_source, arguments.arc2_source, reproduced_root, arguments.packet
        )
        reproduced_artifacts = _artifact_hashes(reproduced_root)
    persisted = _load_json(report_root / "receipt.json")
    if persisted != reproduced:
        raise ValueError("persisted packet receipt does not reproduce exactly")
    if _artifact_hashes(report_root) != reproduced_artifacts:
        raise ValueError("persisted packet artifacts do not reproduce exactly")
    print(f"{persisted['packet_id']}: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
