#!/usr/bin/env python3
"""Run or verify a frozen filename-only ARC12 generalization packet."""

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


_FORBIDDEN_CONTROLLER_TOKENS = (
    "_test_targets",
    "post_answer_validate",
    "expected_output",
    "task_id",
)


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
    completed = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_bytes(source_root: Path, arguments: Sequence[str]) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _relative_repository_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("packet path must remain inside this repository")
    return candidate


def _verify_clean_source(source_root: Path, expected_commit: str) -> None:
    if _git_output(source_root, ["rev-parse", "HEAD"]) != expected_commit:
        raise ValueError(f"source revision does not match pin: {source_root}")
    if _git_output(source_root, ["status", "--porcelain"]):
        raise ValueError(f"source must remain clean/read-only: {source_root}")


def _controller_boundary_holds() -> bool:
    source = (REPOSITORY_ROOT / "src" / "arc123" / "controller.py").read_text(
        encoding="utf-8"
    )
    return not any(token in source for token in _FORBIDDEN_CONTROLLER_TOKENS)


def _verify_frozen_controller(packet: Mapping[str, Any]) -> dict[str, Any]:
    controller = packet.get("frozen_controller")
    if not isinstance(controller, Mapping):
        raise ValueError("frozen packet must declare frozen_controller")
    frozen_commit = controller.get("commit")
    source_files = controller.get("source_files")
    if not isinstance(frozen_commit, str) or not isinstance(source_files, Mapping):
        raise ValueError("frozen controller lacks a commit or source files")
    if _git_output(REPOSITORY_ROOT, ["rev-parse", f"{frozen_commit}^{{commit}}"] ) != frozen_commit:
        raise ValueError("frozen controller commit does not resolve")
    ancestry = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", frozen_commit, "HEAD"],
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise ValueError("frozen controller commit is not an ancestor of HEAD")
    verified_hashes: dict[str, str] = {}
    for raw_path, expected_hash in source_files.items():
        if not isinstance(raw_path, str) or not isinstance(expected_hash, str):
            raise ValueError("frozen controller source file declaration is malformed")
        relative_path = _relative_repository_path(raw_path)
        local_path = REPOSITORY_ROOT / relative_path
        if not local_path.is_file() or _sha256(local_path) != expected_hash:
            raise ValueError(f"frozen controller drifted locally: {relative_path}")
        pinned_bytes = _git_bytes(
            REPOSITORY_ROOT, ["show", f"{frozen_commit}:{relative_path.as_posix()}"]
        )
        if hashlib.sha256(pinned_bytes).hexdigest() != expected_hash:
            raise ValueError(f"frozen controller pin is inconsistent: {relative_path}")
        verified_hashes[relative_path.as_posix()] = expected_hash
    if not _controller_boundary_holds():
        raise ValueError("controller source violates the held-out target boundary")
    return {"commit": frozen_commit, "source_files": verified_hashes}


def _task_records(packet: Mapping[str, Any]) -> list[dict[str, str]]:
    reference = packet.get("cohort_import")
    if not isinstance(reference, Mapping):
        raise ValueError("frozen packet must declare cohort_import")
    raw_path = reference.get("path")
    expected_hash = reference.get("sha256")
    cohort_key = reference.get("cohort_key")
    expected_count = reference.get("task_count")
    expected_per_benchmark = reference.get("per_benchmark_task_count")
    if not all(isinstance(value, str) and value for value in (raw_path, expected_hash, cohort_key)):
        raise ValueError("cohort import lacks a path, hash, or cohort key")
    if not isinstance(expected_count, int) or not isinstance(expected_per_benchmark, int):
        raise ValueError("cohort import lacks expected task counts")
    import_path = REPOSITORY_ROOT / _relative_repository_path(raw_path)
    if _sha256(import_path) != expected_hash:
        raise ValueError("frozen cohort import hash has changed")
    imported = _load_json(import_path)
    live_boundary = imported.get("live_controller_boundary")
    cohort = imported.get(cohort_key)
    if not isinstance(live_boundary, Mapping) or any(value is not False for value in live_boundary.values()):
        raise ValueError("cohort import weakens the live controller boundary")
    if not isinstance(cohort, Mapping) or cohort.get("task_count") != expected_count:
        raise ValueError("cohort import has the wrong task count")
    if cohort.get("source_pins") != packet.get("source_pins"):
        raise ValueError("cohort and packet source pins differ")
    raw_tasks = cohort.get("tasks")
    if not isinstance(raw_tasks, Mapping):
        raise ValueError("cohort import lacks task records")
    tasks: list[dict[str, str]] = []
    for benchmark in ("arc1", "arc2"):
        benchmark_tasks = raw_tasks.get(benchmark)
        if not isinstance(benchmark_tasks, list) or len(benchmark_tasks) != expected_per_benchmark:
            raise ValueError(f"cohort lacks {expected_per_benchmark} {benchmark} tasks")
        for record in benchmark_tasks:
            if not isinstance(record, Mapping):
                raise ValueError("cohort contains malformed task record")
            split = record.get("split")
            task_id = record.get("task_id")
            source_sha256 = record.get("source_sha256")
            if not all(
                isinstance(value, str) and value for value in (split, task_id, source_sha256)
            ):
                raise ValueError("cohort task lacks split, task ID, or source checksum")
            tasks.append(
                {
                    "benchmark": benchmark,
                    "split": split,
                    "task_id": task_id,
                    "source_sha256": source_sha256,
                }
            )
    if len(tasks) != expected_count:
        raise ValueError("cohort has the wrong total task count")
    if len({(task["benchmark"], task["task_id"]) for task in tasks}) != len(tasks):
        raise ValueError("cohort contains duplicate benchmark/task IDs")
    return tasks


def _controller_from_packet(packet: Mapping[str, Any]) -> IterativeHypothesisLearner:
    controller = packet.get("frozen_controller")
    if not isinstance(controller, Mapping) or controller.get("implementation") != "persistent_partial_theory":
        raise ValueError("frozen packet requires persistent_partial_theory")
    families = controller.get("generic_operator_families")
    if not isinstance(families, list) or not all(isinstance(item, str) for item in families):
        raise ValueError("frozen controller has malformed operator families")
    return IterativeHypothesisLearner(
        candidate_limit=int(controller["candidate_limit"]),
        beam_width=int(controller["beam_width"]),
        max_revisions=int(controller["max_revisions"]),
        revision_enabled=bool(controller["revision_enabled"]),
        operator_families=tuple(families),
    )


def _render_report(receipt: Mapping[str, Any], trace: Mapping[str, Any]) -> str:
    outcome = "YES — ALL TEST CELLS MATCH" if receipt["all_cells_match"] else "NO — TEST CELLS DO NOT ALL MATCH"
    lines = [
        f"# {receipt['benchmark'].upper()} `{receipt['task_id']}` {receipt['packet_id']} Brain Surgery Report",
        "",
        f"## Outcome: {outcome}",
        "",
        f"- **Compared positions:** {receipt['compared_position_count']}",
        f"- **Mismatched cells:** {receipt['mismatched_cell_count']}",
        f"- **Training compatibility:** `{receipt['training_exact']}`",
        f"- **Fallback used:** `{receipt['used_fallback']}`",
        f"- **Selected hypothesis:** `{receipt['selected_hypothesis']}`",
        f"- **Source commit:** `{receipt['source_commit']}`",
        f"- **Frozen controller commit:** `{receipt['frozen_controller']['commit']}`",
        "",
        "## Live-Agent Boundary",
        "",
        "The controller receives only visible training input/output examples and test inputs. It receives no task ID, imported cohort metadata, GT feature contract, GT solver, historical decomposition, or held-out output before committing a complete grid. The expected output appears only in post-answer V&V.",
        "",
        "## Corpus-Callosum Visualization",
        "",
        "![corpus-callosum trace](corpus_callosum.svg)",
        "",
        "- Full explicit event record: [`learning_trace.json`](learning_trace.json)",
        "",
        "## Frozen Measurement",
        "",
        "The controller bytes, generic operator vocabulary, source task checksums, and cohort membership were frozen before this task was parsed or scored. This result cannot tune the frozen controller.",
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
    task: Mapping[str, str],
    source_root: Path,
    frozen_controller: Mapping[str, Any],
    report_directory: Path,
) -> dict[str, Any]:
    benchmark = task["benchmark"]
    source_pin = packet["source_pins"][benchmark]
    task_directory = _relative_repository_path(str(source_pin["task_directory"]))
    task_path = source_root / task_directory / task["split"] / f"{task['task_id']}.json"
    if not task_path.is_file() or _sha256(task_path) != task["source_sha256"]:
        raise ValueError(f"frozen source task changed: {task_path}")
    payload = _load_json(task_path)
    environment = ARC12InteractiveEnv.from_task_payload(
        payload,
        provenance={
            "benchmark": benchmark,
            "task_id": task["task_id"],
            "split": task["split"],
            "source_commit": source_pin["commit"],
            "source_task_url": (
                f"{source_pin['repository']}/blob/{source_pin['commit']}/"
                f"{task_directory.as_posix()}/{task['split']}/{task['task_id']}.json"
            ),
        },
    )
    result = _controller_from_packet(packet).solve(
        environment, f"{packet['packet_id']}:anonymous-frozen-measurement"
    )
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
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "benchmark": benchmark,
        "task_id": task["task_id"],
        "task_split": task["split"],
        "source_commit": source_pin["commit"],
        "source_task_url": environment.provenance_for_report()["source_task_url"],
        "frozen_controller": dict(frozen_controller),
        "agent_input_contract": {
            "task_id_passed_to_agent": False,
            "cohort_metadata_passed_to_agent": False,
            "gt_feature_contract_passed_to_agent": False,
            "gt_solver_imported_or_called": False,
            "held_out_outputs_passed_to_agent": False,
        },
        "controller_oracle_boundary_scan": "pass" if _controller_boundary_holds() else "fail",
        "selected_hypothesis": result.selected_hypothesis,
        "training_exact": result.training_exact,
        "used_fallback": result.used_fallback,
        "posterior_mass": result.posterior_mass,
        "all_cells_match": all(item["all_cells_match"] for item in validation),
        "mismatched_cell_count": sum(item["mismatched_cell_count"] for item in validation),
        "compared_position_count": sum(item["compared_position_count"] for item in validation),
        "test_cases": validation,
        "trace_artifacts": {
            "learning_trace": {"path": "learning_trace.json", "sha256": _sha256(trace_path)},
            "corpus_callosum": {"path": "corpus_callosum.svg", "sha256": _sha256(diagram_path)},
        },
    }
    _write_json(report_directory / "receipt.json", receipt)
    report_path = report_directory / "REPORT.md"
    report_path.write_text(_render_report(receipt, result.trace), encoding="utf-8")
    receipt["trace_artifacts"]["report"] = {"path": "REPORT.md", "sha256": _sha256(report_path)}
    _write_json(report_directory / "receipt.json", receipt)
    return receipt


def _default_report_root(packet: Mapping[str, Any]) -> Path:
    raw_path = packet.get("report_root")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("frozen packet lacks a repository-relative report root")
    return REPOSITORY_ROOT / _relative_repository_path(raw_path)


def run_packet(
    arc1_source: Path,
    arc2_source: Path,
    report_root: Path,
    packet_path: Path,
) -> dict[str, Any]:
    packet = _load_json(packet_path)
    if packet.get("external_mutation_allowed") is not False:
        raise ValueError("frozen packet must forbid external repository mutation")
    if packet.get("benchmark_submission_allowed") is not False:
        raise ValueError("frozen packet must forbid benchmark submission")
    frozen_controller = _verify_frozen_controller(packet)
    source_roots = {"arc1": arc1_source, "arc2": arc2_source}
    for benchmark, source_root in source_roots.items():
        _verify_clean_source(source_root, str(packet["source_pins"][benchmark]["commit"]))
    receipts = [
        _task_receipt(
            packet,
            task,
            source_roots[task["benchmark"]],
            frozen_controller,
            report_root / task["benchmark"] / task["task_id"],
        )
        for task in _task_records(packet)
    ]
    exact_by_benchmark = {
        benchmark: sum(
            receipt["all_cells_match"] for receipt in receipts if receipt["benchmark"] == benchmark
        )
        for benchmark in ("arc1", "arc2")
    }
    summary = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "claim_boundary": packet["claim_boundary"],
        "controller_oracle_boundary_scan": "pass",
        "frozen_controller": frozen_controller,
        "attempt_count": len(receipts),
        "exact_solve_count": sum(receipt["all_cells_match"] for receipt in receipts),
        "exact_solve_count_by_benchmark": exact_by_benchmark,
        "complete_wrong_count": sum(not receipt["all_cells_match"] for receipt in receipts),
        "training_exact_count": sum(receipt["training_exact"] for receipt in receipts),
        "fallback_count": sum(receipt["used_fallback"] for receipt in receipts),
        "attempts": [
            {
                "benchmark": receipt["benchmark"],
                "task_id": receipt["task_id"],
                "all_cells_match": receipt["all_cells_match"],
                "training_exact": receipt["training_exact"],
                "used_fallback": receipt["used_fallback"],
                "selected_hypothesis": receipt["selected_hypothesis"],
            }
            for receipt in receipts
        ],
    }
    _write_json(report_root / "receipt.json", summary)
    per_benchmark_denominator = len(receipts) // 2
    lines = [
        str(packet["report_title"]),
        "",
        f"- Attempts: `{summary['attempt_count']}`",
        f"- Exact post-answer solves: `{summary['exact_solve_count']}/{summary['attempt_count']}`",
        f"- ARC1 exact solves: `{exact_by_benchmark['arc1']}/{per_benchmark_denominator}`",
        f"- ARC2 exact solves: `{exact_by_benchmark['arc2']}/{per_benchmark_denominator}`",
        f"- Complete wrong predictions retained: `{summary['complete_wrong_count']}`",
        f"- Frozen controller: `{frozen_controller['commit']}`",
        "",
        "| Benchmark | Task | Full result | Training exact | Fallback | Report |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for receipt in receipts:
        report = f"{receipt['benchmark']}/{receipt['task_id']}/REPORT.md"
        lines.append(
            f"| {receipt['benchmark'].upper()} | `{receipt['task_id']}` | "
            f"{'YES' if receipt['all_cells_match'] else 'NO'} | "
            f"`{receipt['training_exact']}` | `{receipt['used_fallback']}` | "
            f"[brain surgery]({report}) |"
        )
    lines.extend(
        [
            "",
            "Every task is a complete frozen-controller commitment followed by post-answer all-cell V&V. Every NO remains in the immutable denominator. This packet cannot tune the frozen controller.",
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
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--report-root", type=Path)
    arguments = parser.parse_args()
    packet = _load_json(arguments.packet)
    report_root = arguments.report_root or _default_report_root(packet)
    if arguments.run:
        if report_root.exists():
            raise ValueError(f"refusing to overwrite existing report root: {report_root}")
        summary = run_packet(
            arguments.arc1_source,
            arguments.arc2_source,
            report_root,
            arguments.packet,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
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
        raise ValueError("persisted frozen packet receipt does not reproduce exactly")
    if _artifact_hashes(report_root) != reproduced_artifacts:
        raise ValueError("persisted frozen packet artifacts do not reproduce exactly")
    print(f"{persisted['packet_id']}: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
