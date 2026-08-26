#!/usr/bin/env python3
"""Run forward-only vs exact forward/backward observational synthesis on opened ARC tasks.

The script is intentionally separate from the live controller packet runner. It
is an architecture ablation: both modes see the same training pairs and test
*inputs*. The held-out test outputs are retained in a quarantined local variable
and used only after both searches have returned predictions/singularity status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from arc123.model import Grid, TrainingPair
from arc123.observational_arc_grammar import DEFAULT_OBSERVATIONAL_ARC_PRIMITIVES
from arc123.observational_program_synthesis import (
    ObservationalSearchResult,
    compare_forward_only_to_forward_backward,
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _grid(payload: Sequence[Sequence[int]]) -> Grid:
    return tuple(tuple(int(value) for value in row) for row in payload)


def _task_path(packet: Mapping[str, Any], task: Mapping[str, Any], source_root: Path) -> Path:
    pin = packet["source_pins"][task["benchmark"]]
    directory = Path(str(pin.get("task_directory", "data")))
    if directory.is_absolute() or ".." in directory.parts:
        raise ValueError("task_directory must remain inside source root")
    return source_root / directory / str(task["split"]) / f"{task['task_id']}.json"


def _prediction_fiber(result: ObservationalSearchResult, train_count: int) -> tuple[tuple[Grid, ...], ...]:
    groups = {
        tuple(state.values[train_count:])
        for state in result.exact_grid_states
    }
    # Exact Grid states contain only Grid values in the suffix by construction.
    return tuple(sorted(groups, key=repr))  # type: ignore[return-value]


def _committed_prediction(
    result: ObservationalSearchResult,
    train_count: int,
) -> tuple[Grid, ...] | None:
    fiber = _prediction_fiber(result, train_count)
    return fiber[0] if len(fiber) == 1 else None


def _mode_receipt(result: ObservationalSearchResult, train_count: int) -> dict[str, Any]:
    fiber = _prediction_fiber(result, train_count)
    return {
        "generated_term_count": result.generated_term_count,
        "quotient_state_count": result.quotient_state_count,
        "terminal_candidate_count": result.terminal_candidate_count,
        "backward_constraint_check_count": result.backward_constraint_check_count,
        "backward_pruned_terminal_term_count": result.backward_pruned_terminal_term_count,
        "exact_grid_state_count": len(result.exact_grid_states),
        "minimum_exact_cost": result.minimum_exact_cost,
        "exact_test_prediction_group_count": result.exact_test_prediction_group_count,
        "prediction_singularity": result.has_prediction_singularity,
        "prediction_fiber_size": len(fiber),
        "exact_term_names": [state.term.name for state in result.exact_grid_states],
    }


def _validate_prediction(prediction: tuple[Grid, ...] | None, held_out: tuple[Grid, ...]) -> dict[str, Any]:
    if prediction is None:
        return {
            "committed": False,
            "all_cells_match": False,
            "mismatched_cell_count": None,
        }
    if len(prediction) != len(held_out):
        return {
            "committed": True,
            "all_cells_match": False,
            "mismatched_cell_count": None,
        }
    mismatches = 0
    comparable = True
    for predicted, target in zip(prediction, held_out):
        if len(predicted) != len(target) or any(len(a) != len(b) for a, b in zip(predicted, target)):
            comparable = False
            break
        mismatches += sum(
            a != b
            for predicted_row, target_row in zip(predicted, target)
            for a, b in zip(predicted_row, target_row)
        )
    return {
        "committed": True,
        "all_cells_match": comparable and mismatches == 0,
        "mismatched_cell_count": mismatches if comparable else None,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _run_task(
    packet: Mapping[str, Any],
    task: Mapping[str, Any],
    source_roots: Mapping[str, Path],
) -> dict[str, Any]:
    benchmark = str(task["benchmark"])
    task_path = _task_path(packet, task, source_roots[benchmark])
    payload = _load_json(task_path)

    training: tuple[TrainingPair, ...] = tuple(
        (_grid(pair["input"]), _grid(pair["output"])) for pair in payload["train"]
    )
    # LIVE SEARCH BOUNDARY: only test inputs leave this construction site.
    test_inputs: tuple[Grid, ...] = tuple(_grid(pair["input"]) for pair in payload["test"])

    ablation = compare_forward_only_to_forward_backward(
        training,
        test_inputs,
        DEFAULT_OBSERVATIONAL_ARC_PRIMITIVES,
        terminal_primitive_names=tuple(packet["search"]["terminal_renderers"]),
        max_cost=int(packet["search"]["max_cost"]),
    )

    train_count = len(training)
    forward_prediction = _committed_prediction(ablation.forward_only, train_count)
    fb_prediction = _committed_prediction(ablation.forward_backward, train_count)
    forward_fiber = _prediction_fiber(ablation.forward_only, train_count)
    fb_fiber = _prediction_fiber(ablation.forward_backward, train_count)

    # POST-SEARCH V&V BOUNDARY: held-out outputs are materialized only now.
    held_out: tuple[Grid, ...] = tuple(_grid(pair["output"]) for pair in payload["test"])

    forward_validation = _validate_prediction(forward_prediction, held_out)
    fb_validation = _validate_prediction(fb_prediction, held_out)
    state_reduction = (
        ablation.forward_only.quotient_state_count
        - ablation.forward_backward.quotient_state_count
    )
    reduction_fraction = (
        state_reduction / ablation.forward_only.quotient_state_count
        if ablation.forward_only.quotient_state_count
        else 0.0
    )

    return {
        "benchmark": benchmark,
        "split": task["split"],
        "task_id": task["task_id"],
        "source_commit": packet["source_pins"][benchmark]["commit"],
        "agent_input_contract": {
            "task_id_used_by_synthesizer": False,
            "held_out_outputs_passed_to_forward_only": False,
            "held_out_outputs_passed_to_forward_backward": False,
            "grammar_identical_between_modes": True,
            "cost_bound_identical_between_modes": True,
            "test_inputs_identical_between_modes": True,
        },
        "forward_only": {
            **_mode_receipt(ablation.forward_only, train_count),
            "post_answer_validation": forward_validation,
        },
        "forward_backward": {
            **_mode_receipt(ablation.forward_backward, train_count),
            "post_answer_validation": fb_validation,
        },
        "invariants": {
            "exact_prediction_fiber_equal": forward_fiber == fb_fiber,
            "prediction_singularity_equal": (
                ablation.forward_only.has_prediction_singularity
                == ablation.forward_backward.has_prediction_singularity
            ),
            "minimum_exact_cost_equal": (
                ablation.forward_only.minimum_exact_cost
                == ablation.forward_backward.minimum_exact_cost
            ),
        },
        "search_effect": {
            "quotient_state_reduction": state_reduction,
            "quotient_state_reduction_fraction": reduction_fraction,
            "backward_pruned_terminal_term_count": (
                ablation.forward_backward.backward_pruned_terminal_term_count
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--arc1-source", required=True, type=Path)
    parser.add_argument("--arc2-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    packet = _load_json(args.packet)
    source_roots = {"arc1": args.arc1_source, "arc2": args.arc2_source}
    tasks = [
        _run_task(packet, task, source_roots)
        for task in packet["tasks"]
    ]
    receipt = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "claim_boundary": packet["claim_boundary"],
        "packet_sha256": _sha256(args.packet),
        "task_count": len(tasks),
        "all_prediction_fibers_preserved": all(
            task["invariants"]["exact_prediction_fiber_equal"] for task in tasks
        ),
        "forward_only_exact_solve_count": sum(
            task["forward_only"]["post_answer_validation"]["all_cells_match"] for task in tasks
        ),
        "forward_backward_exact_solve_count": sum(
            task["forward_backward"]["post_answer_validation"]["all_cells_match"] for task in tasks
        ),
        "tasks_with_positive_state_reduction": sum(
            task["search_effect"]["quotient_state_reduction"] > 0 for task in tasks
        ),
        "total_quotient_state_reduction": sum(
            task["search_effect"]["quotient_state_reduction"] for task in tasks
        ),
        "total_backward_pruned_terminal_terms": sum(
            task["search_effect"]["backward_pruned_terminal_term_count"] for task in tasks
        ),
        "tasks": tasks,
    }
    _write_json(args.output, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
