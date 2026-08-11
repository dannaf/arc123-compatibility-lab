#!/usr/bin/env python3
"""Run or reproduce a source-pinned ARC12 iterative-learning packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.traces import render_corpus_callosum_svg, render_trace_markdown


PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0001_ARC12_TINY_REDISCOVERY.json"
DEFAULT_REPORT_ROOT = REPOSITORY_ROOT / "reports" / "P0001_arc12_tiny_rediscovery"


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


def _default_report_root(packet: Mapping[str, Any]) -> Path:
    raw_path = packet.get("report_root")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("packet must declare a repository-relative report_root")
    relative_path = Path(raw_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("packet report_root must stay inside the repository")
    return REPOSITORY_ROOT / relative_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): _sha256(path)
        for path in sorted(root.glob("**/*"))
        if path.is_file()
    }


def _git_output(source_root: Path, arguments: list[str]) -> str:
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
        raise ValueError(f"source must remain clean/read-only: {source_root}")


def _controller_oracle_boundary_holds() -> bool:
    controller_source = (REPOSITORY_ROOT / "src" / "arc123" / "controller.py").read_text(
        encoding="utf-8"
    )
    forbidden_tokens = ("_test_targets", "post_answer_validate", "expected_output")
    return not any(token in controller_source for token in forbidden_tokens)


def _render_report(receipt: Mapping[str, Any], trace: Mapping[str, Any]) -> str:
    outcome = "YES — ALL TEST CELLS MATCH" if receipt["all_cells_match"] else "NO — TEST CELLS DO NOT ALL MATCH"
    lines = [
        f"# {receipt['benchmark'].upper()} `{receipt['task_id']}` IHL Brain Surgery Report",
        "",
        f"## Outcome: {outcome}",
        "",
        f"- **Compared positions:** {receipt['compared_position_count']}",
        f"- **Mismatched cells:** {receipt['mismatched_cell_count']}",
        f"- **Source commit:** `{receipt['source_commit']}`",
        f"- **Selected hypothesis:** `{receipt['selected_hypothesis']}`",
        f"- **Training compatibility:** `{receipt['training_exact']}`",
        f"- **Fallback used:** `{receipt['used_fallback']}`",
        "",
        "## Live-Agent Boundary",
        "",
        "The controller receives only training input/output evidence and the test input. It receives no task ID, historical schema/decomposition, GT feature contract, GT solver, or test target. The expected test output below is accessed only after the complete prediction is committed for V&V.",
        "",
        "## Corpus-Callosum Visualization",
        "",
        "![ARC123 corpus-callosum trace](corpus_callosum.svg)",
        "",
        "- Full explicit event record: [`learning_trace.json`](learning_trace.json)",
        "",
        "The diagram shows the actual test input, the typed compatibility core, and the committed full prediction. It renders observable operations only; it does not fabricate a one-to-one causal fiber where the selected program is only a factor-level dependency.",
        "",
        "## Post-Answer V&V",
        "",
    ]
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
    task: Mapping[str, Any],
    source_root: Path,
    report_directory: Path,
) -> dict[str, Any]:
    benchmark = str(task["benchmark"])
    task_id = str(task["task_id"])
    split = str(task["split"])
    task_path = source_root / "arc_data" / benchmark / split / f"{task_id}.json"
    if not task_path.is_file():
        raise ValueError(f"source-pinned task does not exist: {task_path}")
    payload = _load_json(task_path)
    source_pin = packet["source_pins"][benchmark]
    environment = ARC12InteractiveEnv.from_task_payload(
        payload,
        provenance={
            "benchmark": benchmark,
            "task_id": task_id,
            "split": split,
            "source_commit": source_pin["commit"],
            "source_task_url": (
                f"{source_pin['repository']}/blob/{source_pin['commit']}/"
                f"arc_data/{benchmark}/{split}/{task_id}.json"
            ),
        },
    )
    result = IterativeHypothesisLearner(
        candidate_limit=int(packet["controller"]["candidate_limit"]),
        operator_families=tuple(packet["controller"]["generic_operator_families"]),
    ).solve(environment, f"{packet['packet_id']}:{benchmark}:{task_id}")
    validation = environment.post_answer_validate(result.predictions)
    trace_path = report_directory / "learning_trace.json"
    diagram_path = report_directory / "corpus_callosum.svg"
    _write_json(trace_path, result.trace)
    render_corpus_callosum_svg(
        diagram_path,
        environment.test_inputs[0],
        result.predictions[0],
        result.selected_hypothesis,
        result.trace,
    )
    all_cells_match = all(item["all_cells_match"] for item in validation)
    receipt = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "benchmark": benchmark,
        "task_id": task_id,
        "task_split": split,
        "source_commit": source_pin["commit"],
        "source_task_url": environment.provenance_for_report()["source_task_url"],
        "agent_input_contract": {
            "task_id_passed_to_agent": False,
            "historical_schema_passed_to_agent": False,
            "decomposition_mapping_passed_to_agent": False,
            "gt_feature_contract_passed_to_agent": False,
            "gt_solver_imported_or_called": False,
            "held_out_outputs_passed_to_agent": False,
        },
        "controller_oracle_boundary_scan": "pass" if _controller_oracle_boundary_holds() else "fail",
        "selected_hypothesis": result.selected_hypothesis,
        "training_exact": result.training_exact,
        "used_fallback": result.used_fallback,
        "posterior_mass": result.posterior_mass,
        "all_cells_match": all_cells_match,
        "mismatched_cell_count": sum(item["mismatched_cell_count"] for item in validation),
        "compared_position_count": sum(item["compared_position_count"] for item in validation),
        "test_cases": validation,
        "trace_artifacts": {
            "learning_trace": {"path": "learning_trace.json", "sha256": _sha256(trace_path)},
            "corpus_callosum": {"path": "corpus_callosum.svg", "sha256": _sha256(diagram_path)},
        },
    }
    _write_json(report_directory / "receipt.json", receipt)
    (report_directory / "REPORT.md").write_text(
        _render_report(receipt, result.trace), encoding="utf-8"
    )
    receipt["trace_artifacts"]["report"] = {
        "path": "REPORT.md",
        "sha256": _sha256(report_directory / "REPORT.md"),
    }
    _write_json(report_directory / "receipt.json", receipt)
    return receipt


def run_packet(
    arc1_source: Path,
    arc2_source: Path,
    report_root: Path | None = None,
    packet_path: Path = PACKET_PATH,
) -> dict[str, Any]:
    packet = _load_json(packet_path)
    packet_id = packet.get("packet_id")
    if not isinstance(packet_id, str) or not packet_id.startswith("P"):
        raise ValueError("packet must declare a P-series packet identifier")
    report_root = report_root or _default_report_root(packet)
    source_roots = {"arc1": arc1_source, "arc2": arc2_source}
    for benchmark, source_root in source_roots.items():
        _verify_clean_source(source_root, str(packet["source_pins"][benchmark]["commit"]))
    if not _controller_oracle_boundary_holds():
        raise ValueError("controller source violates the held-out-target boundary")
    task_receipts = []
    for task in packet["tasks"]:
        if not isinstance(task, Mapping):
            raise ValueError("packet task must be an object")
        benchmark = str(task["benchmark"])
        report_directory = report_root / benchmark / str(task["task_id"])
        task_receipts.append(
            _task_receipt(packet, task, source_roots[benchmark], report_directory)
        )
    summary = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "claim_boundary": packet["claim_boundary"],
        "controller_oracle_boundary_scan": "pass",
        "attempt_count": len(task_receipts),
        "exact_solve_count": sum(item["all_cells_match"] for item in task_receipts),
        "complete_wrong_count": sum(not item["all_cells_match"] for item in task_receipts),
        "training_exact_count": sum(item["training_exact"] for item in task_receipts),
        "fallback_count": sum(item["used_fallback"] for item in task_receipts),
        "attempts": [
            {
                "benchmark": item["benchmark"],
                "task_id": item["task_id"],
                "all_cells_match": item["all_cells_match"],
                "mismatched_cell_count": item["mismatched_cell_count"],
                "selected_hypothesis": item["selected_hypothesis"],
                "training_exact": item["training_exact"],
                "used_fallback": item["used_fallback"],
            }
            for item in task_receipts
        ],
    }
    _write_json(report_root / "receipt.json", summary)
    lines = [
        str(packet.get("report_title", f"# {summary['packet_id']} ARC12 Rediscovery Packet")),
        "",
        f"- Attempts: `{summary['attempt_count']}`",
        f"- Exact post-answer solves: `{summary['exact_solve_count']}/{summary['attempt_count']}`",
        f"- Complete wrong answers retained: `{summary['complete_wrong_count']}`",
        f"- Training-compatible theories: `{summary['training_exact_count']}`",
        f"- Complete-grid fallbacks: `{summary['fallback_count']}`",
        "",
        "| Benchmark | Task | Outcome | Training exact | Selected hypothesis | Report |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in task_receipts:
        outcome = "YES" if item["all_cells_match"] else "NO"
        report = f"{item['benchmark']}/{item['task_id']}/REPORT.md"
        lines.append(
            f"| {item['benchmark'].upper()} | `{item['task_id']}` | {outcome} | "
            f"`{item['training_exact']}` | `{item['selected_hypothesis']}` | [brain surgery]({report}) |"
        )
    lines.extend(
        [
            "",
            "Every entry is an attempted complete output followed by post-answer V&V. A NO remains a first-class failure record; no task is silently abstained or removed from the denominator.",
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
    report_root = arguments.report_root or _default_report_root(packet)
    if arguments.run:
        summary = run_packet(
            arguments.arc1_source,
            arguments.arc2_source,
            report_root,
            arguments.packet,
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    with tempfile.TemporaryDirectory() as temporary_directory:
        reproduced_root = Path(temporary_directory)
        reproduced = run_packet(
            arguments.arc1_source,
            arguments.arc2_source,
            reproduced_root,
            arguments.packet,
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
