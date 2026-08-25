#!/usr/bin/env python3
"""Run ARC12 packets whose source pins declare their own task_directory.

This is a thin compatibility layer over run_arc12_tiny_rediscovery.py.  It keeps
all existing receipt/report/oracle-boundary logic, but removes the historical
hard-code that assumed every source repository stored tasks below
`arc_data/<benchmark>/...`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPOSITORY_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import run_arc12_tiny_rediscovery as base
from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.traces import render_corpus_callosum_svg


def _declared_task_path(
    packet: Mapping[str, Any], task: Mapping[str, Any], source_root: Path
) -> Path:
    benchmark = str(task["benchmark"])
    split = str(task["split"])
    task_id = str(task["task_id"])
    source_pin = packet["source_pins"][benchmark]
    raw_directory = source_pin.get("task_directory", f"arc_data/{benchmark}")
    task_directory = Path(str(raw_directory))
    if task_directory.is_absolute() or ".." in task_directory.parts:
        raise ValueError("source task_directory must be relative and stay inside source repo")
    return source_root / task_directory / split / f"{task_id}.json"


def _task_receipt(
    packet: Mapping[str, Any],
    task: Mapping[str, Any],
    source_root: Path,
    report_directory: Path,
) -> dict[str, Any]:
    benchmark = str(task["benchmark"])
    task_id = str(task["task_id"])
    split = str(task["split"])
    source_pin = packet["source_pins"][benchmark]
    task_path = _declared_task_path(packet, task, source_root)
    if not task_path.is_file():
        raise ValueError(f"source-pinned task does not exist: {task_path}")
    payload = base._load_json(task_path)
    task_directory = str(source_pin.get("task_directory", f"arc_data/{benchmark}")).strip("/")
    environment = ARC12InteractiveEnv.from_task_payload(
        payload,
        provenance={
            "benchmark": benchmark,
            "task_id": task_id,
            "split": split,
            "source_commit": source_pin["commit"],
            "source_task_url": (
                f"{source_pin['repository']}/blob/{source_pin['commit']}/"
                f"{task_directory}/{split}/{task_id}.json"
            ),
        },
    )
    result = IterativeHypothesisLearner(
        candidate_limit=int(packet["controller"]["candidate_limit"]),
        operator_families=tuple(packet["controller"]["generic_operator_families"]),
    ).solve(environment, f"{packet['packet_id']}:{benchmark}:{task_id}")

    # The held-out target enters only here, after solve() returns a complete
    # committed prediction.  This is the same post-answer V&V boundary as P0002.
    validation = environment.post_answer_validate(result.predictions)
    trace_path = report_directory / "learning_trace.json"
    diagram_path = report_directory / "corpus_callosum.svg"
    base._write_json(trace_path, result.trace)
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
        "controller_oracle_boundary_scan": (
            "pass" if base._controller_oracle_boundary_holds() else "fail"
        ),
        "selected_hypothesis": result.selected_hypothesis,
        "training_exact": result.training_exact,
        "used_fallback": result.used_fallback,
        "posterior_mass": result.posterior_mass,
        "all_cells_match": all_cells_match,
        "mismatched_cell_count": sum(item["mismatched_cell_count"] for item in validation),
        "compared_position_count": sum(item["compared_position_count"] for item in validation),
        "test_cases": validation,
        "trace_artifacts": {
            "learning_trace": {"path": "learning_trace.json", "sha256": base._sha256(trace_path)},
            "corpus_callosum": {"path": "corpus_callosum.svg", "sha256": base._sha256(diagram_path)},
        },
    }
    base._write_json(report_directory / "receipt.json", receipt)
    report_path = report_directory / "REPORT.md"
    report_path.write_text(base._render_report(receipt, result.trace), encoding="utf-8")
    receipt["trace_artifacts"]["report"] = {
        "path": "REPORT.md",
        "sha256": base._sha256(report_path),
    }
    base._write_json(report_directory / "receipt.json", receipt)
    return receipt


def main() -> int:
    # Reuse the mature packet CLI/reproduction logic, replacing only the task
    # path adapter.  Historical runners and persisted P0001/P0002 artifacts stay
    # byte-for-byte untouched.
    base._task_receipt = _task_receipt
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
