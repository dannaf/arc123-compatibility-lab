#!/usr/bin/env python3
"""Run or verify the source-pinned ARC3 learned-mechanics evidence packet."""

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

from arc123.adapters.arc3 import SourcePinnedARC3ReplayWorld
from arc123.controller import IterativeHypothesisLearner
from arc123.model import grid_from
from arc123.traces import render_arc3_mechanics_svg, render_trace_markdown


PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0009_ARC3_LEARNED_MECHANICS_L1.json"
_FORBIDDEN_AGENT_TOKENS = (
    "_records",
    "offline_provenance_for_report",
    "source_commit",
    "source_path",
    "expected_action_sequence",
)


def _load_json(file_path: Path) -> dict[str, Any]:
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{file_path} must contain a JSON object")
    return payload


def _write_json(file_path: Path, payload: Mapping[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _artifacts(root: Path) -> dict[str, str]:
    return {
        str(file_path.relative_to(root)): _sha256(file_path)
        for file_path in sorted(root.glob("**/*"))
        if file_path.is_file()
    }


def _git_output(source_root: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_bytes(source_root: Path, arguments: Sequence[str]) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=True,
        capture_output=True,
    )
    return result.stdout


def _verify_source_pin(source_root: Path, source_pin: Mapping[str, Any]) -> None:
    commit = source_pin.get("commit")
    source_path = source_pin.get("path")
    expected_sha256 = source_pin.get("sha256")
    if not all(isinstance(value, str) and value for value in (commit, source_path, expected_sha256)):
        raise ValueError("P0009 source pin is incomplete")
    resolved = _git_output(source_root, ["rev-parse", f"{commit}^{{commit}}"])
    if resolved != commit:
        raise ValueError("SingularityML source does not contain the immutable P0009 commit")
    raw_source = _git_bytes(source_root, ["show", f"{commit}:{source_path}"])
    if hashlib.sha256(raw_source).hexdigest() != expected_sha256:
        raise ValueError("P0009 source pin content hash does not match")


def _relative_repository_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("packet report root must remain inside this repository")
    return candidate


def _default_report_root(packet: Mapping[str, Any]) -> Path:
    raw_path = packet.get("report_root")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("packet lacks a repository-relative report_root")
    return REPOSITORY_ROOT / _relative_repository_path(raw_path)


def _controller_boundary_holds() -> bool:
    agent_sources = (
        REPOSITORY_ROOT / "src" / "arc123" / "controller.py",
        REPOSITORY_ROOT / "src" / "arc123" / "arc3_mechanics.py",
    )
    source = "\n".join(file_path.read_text(encoding="utf-8") for file_path in agent_sources)
    return not any(token in source for token in _FORBIDDEN_AGENT_TOKENS)


def _acceptance(receipt: Mapping[str, Any], packet: Mapping[str, Any]) -> bool:
    requirements = packet.get("acceptance")
    if not isinstance(requirements, Mapping):
        raise ValueError("P0009 packet lacks acceptance requirements")
    choices = receipt.get("action_choices")
    if not isinstance(choices, list):
        return False
    strictly_reduced = bool(choices) and all(
        isinstance(choice, Mapping)
        and choice.get("goal_distance_after") < choice.get("goal_distance_before")
        for choice in choices
    )
    return bool(
        receipt.get("mechanics_learning_confirmed")
        and receipt.get("learned_action_effect_count", 0)
        >= int(requirements["minimum_learned_action_effects"])
        and (
            not requirements["require_non_default_goal_action"]
            or receipt.get("non_default_action_confirmed")
        )
        and (
            not requirements["require_strict_visible_goal_distance_reduction"]
            or strictly_reduced
        )
        and (
            not requirements["require_recorded_level_progress"]
            or receipt.get("level_progress_observed")
        )
    )


def _report_text(receipt: Mapping[str, Any], trace: Mapping[str, Any]) -> str:
    outcome = (
        "YES — LEARNED MECHANICS CONTRIBUTED TO RECORDED LEVEL PROGRESS"
        if receipt["acceptance_passed"]
        else "NO — LEARNED MECHANICS DID NOT MEET THE PRE-REGISTERED GATE"
    )
    requirements = receipt["acceptance_requirements"]
    choices = receipt["action_choices"]
    lines = [
        "# ARC3 `ls20` L1 Learned-Mechanics Brain Surgery Report",
        "",
        f"## Outcome: {outcome}",
        "",
        f"- **Prior public transitions consumed:** `{receipt['history_transition_count']}`",
        f"- **Learned action effects:** `{receipt['learned_action_effect_count']}`",
        f"- **First action non-default:** `{receipt['non_default_action_confirmed']}`",
        f"- **Recorded levels completed:** `{receipt['initial_progress']}` → `{receipt['final_progress']}`",
        f"- **Source commit:** `{receipt['source_pin']['commit']}`",
        "- **General ARC3 / ARC-AGI solver claim:** `NO`",
        "",
        "## Live-Agent Boundary",
        "",
        "The controller receives only public transitions before the live cursor, then one current public frame and currently available actions. It receives no source provenance, cursor, future action sequence, future frame, simulator, post-hoc rule, oracle diff, or reasoning annotation. A non-recorded action is refused rather than simulated.",
        "",
        "## Corpus-Callosum Visualization",
        "",
        "![P0009 learned-mechanics corpus-callosum trace](corpus_callosum.svg)",
        "",
        "- Full explicit action/evidence/revision record: [`learning_trace.json`](learning_trace.json)",
        "",
        "## Pre-Registered Gate",
        "",
        f"- At least `{requirements['minimum_learned_action_effects']}` observed action effects: `{receipt['learned_action_effect_count'] >= requirements['minimum_learned_action_effects']}`",
        f"- Non-default goal-directed action: `{receipt['non_default_action_confirmed']}`",
        f"- Every selected action reduces the visible relation: `{receipt['goal_distance_reduction_confirmed']}`",
        f"- Recorded level progress: `{receipt['level_progress_observed']}`",
        f"- **Gate passed:** `{receipt['acceptance_passed']}`",
        "",
        "## Observed Action Choices",
        "",
    ]
    for action_index, choice in enumerate(choices, start=1):
        action = choice.get("action", {})
        parameters = action.get("parameters", {}) if isinstance(action, Mapping) else {}
        lines.append(
            "- "
            f"`{action_index}` `{parameters.get('key', '?')}`: visible squared distance "
            f"`{choice.get('goal_distance_before')}` → `{choice.get('goal_distance_after')}`; "
            f"non-default=`{choice.get('is_non_default')}`; "
            f"observed match=`{choice.get('prediction_matched_observation')}`."
        )
    lines.extend(
        [
            "",
            "## V&V",
            "",
            f"- Source-pinned trajectory: [{receipt['source_pin']['path']}]({receipt['source_pin']['url']})",
            f"- Source content SHA-256: `{receipt['source_pin']['sha256']}`",
            f"- Controller oracle-boundary scan: `{receipt['controller_oracle_boundary_scan']}`",
            "- Re-run with `--verify` reconstructs every artifact in a temporary directory and compares all SHA-256 hashes.",
            "- This is bounded causal replay evidence only; it is not a benchmark submission or a claim of broad ARC capability.",
            "",
            render_trace_markdown(trace).rstrip(),
            "",
        ]
    )
    return "\n".join(lines)


def run_packet(
    singularityml_root: Path,
    report_root: Path | None = None,
    packet_path: Path = PACKET_PATH,
) -> dict[str, Any]:
    packet = _load_json(packet_path)
    if packet.get("external_mutation_allowed") is not False:
        raise ValueError("P0009 must forbid external repository mutation")
    if packet.get("benchmark_submission_allowed") is not False:
        raise ValueError("P0009 must forbid benchmark submission")
    source_pin = packet.get("source_pin")
    public_history = packet.get("public_history")
    controller = packet.get("controller")
    if not isinstance(source_pin, Mapping) or not isinstance(public_history, Mapping):
        raise ValueError("P0009 packet lacks its source pin or public-history contract")
    if not isinstance(controller, Mapping):
        raise ValueError("P0009 packet lacks its controller contract")
    _verify_source_pin(singularityml_root, source_pin)
    if not _controller_boundary_holds():
        raise ValueError("ARC3 mechanics controller violates the source/future-action boundary")
    resolved_report_root = report_root or _default_report_root(packet)
    if resolved_report_root.exists() and any(resolved_report_root.iterdir()):
        raise ValueError("P0009 refuses to overwrite an existing report root")
    initial_cursor = public_history.get("initial_cursor")
    transition_count = public_history.get("transition_count")
    if not isinstance(initial_cursor, int) or not isinstance(transition_count, int):
        raise ValueError("P0009 public-history cursor/count must be integers")
    if initial_cursor != transition_count:
        raise ValueError("P0009 requires one history transition per pre-live cursor step")
    world = SourcePinnedARC3ReplayWorld.from_git_source(
        singularityml_root,
        str(source_pin["commit"]),
        str(source_pin["path"]),
        source_repository=str(source_pin["repository"]),
        world_id="arc3-ls20-l1-learned-mechanics",
        initial_cursor=initial_cursor,
    )
    initial_observation = world.observe()
    history = world.observed_history()
    if len(history) != transition_count:
        raise ValueError("adapter returned the wrong bounded public-history length")
    serialized_history = [feedback.as_dict() for feedback in history]
    serialized_history_text = json.dumps(serialized_history, ensure_ascii=False, sort_keys=True)
    if any(token in serialized_history_text for token in ("source_commit", "source_path", "repository")):
        raise ValueError("adapter leaked source provenance into the controller history")
    result = IterativeHypothesisLearner().run_external_mechanics_episode(
        world,
        history,
        max_actions=int(controller["max_actions"]),
        episode_id=packet["packet_id"],
    )
    final_observation = world.observe()
    trace_path = resolved_report_root / "learning_trace.json"
    diagram_path = resolved_report_root / "corpus_callosum.svg"
    _write_json(trace_path, result.trace)
    before_grid = grid_from(initial_observation.payload["frame"], "P0009 initial public frame")
    after_grid = grid_from(final_observation.payload["frame"], "P0009 final public frame")
    result_payload = {
        "final_theory": result.final_theory,
        "action_choices": list(result.action_choices),
        "history_transition_count": result.history_transition_count,
        "initial_progress": result.initial_progress,
        "final_progress": result.final_progress,
    }
    render_arc3_mechanics_svg(diagram_path, before_grid, after_grid, result_payload)
    provenance = world.offline_provenance_for_report()
    learned_motion_model = result.final_theory.get("learned_motion_model", {})
    effects = learned_motion_model.get("action_effects", []) if isinstance(learned_motion_model, Mapping) else []
    action_choices = list(result.action_choices)
    goal_distance_reduction_confirmed = bool(action_choices) and all(
        choice["goal_distance_after"] < choice["goal_distance_before"]
        for choice in action_choices
    )
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "claim_boundary": packet["claim_boundary"],
        "source_pin": provenance,
        "initial_learned_store": controller["initial_learned_store"],
        "forbidden_live_inputs": controller["forbidden_live_inputs"],
        "history_transition_count": result.history_transition_count,
        "initial_cursor": initial_cursor,
        "agent_input_contract": {
            "source_provenance_passed_to_agent": False,
            "initial_cursor_passed_to_agent": False,
            "future_action_sequence_passed_to_agent": False,
            "future_frame_passed_to_agent": False,
            "game_simulator_called": False,
            "post_hoc_rule_passed_to_agent": False,
            "reasoning_annotation_passed_to_agent": False,
        },
        "controller_oracle_boundary_scan": "pass" if _controller_boundary_holds() else "fail",
        "learned_action_effect_count": len(effects),
        "mechanics_learning_confirmed": result.mechanics_learning_confirmed,
        "goal_directed_action_confirmed": result.goal_directed_action_confirmed,
        "non_default_action_confirmed": result.non_default_action_confirmed,
        "goal_distance_reduction_confirmed": goal_distance_reduction_confirmed,
        "level_progress_observed": result.level_progress_observed,
        "initial_progress": result.initial_progress,
        "final_progress": result.final_progress,
        "action_choices": action_choices,
        "transitions": list(result.transitions),
        "final_theory": result.final_theory,
        "acceptance_requirements": dict(packet["acceptance"]),
        "trace_artifacts": {
            "learning_trace": {"path": "learning_trace.json", "sha256": _sha256(trace_path)},
            "corpus_callosum": {"path": "corpus_callosum.svg", "sha256": _sha256(diagram_path)},
        },
    }
    receipt["acceptance_passed"] = _acceptance(receipt, packet)
    _write_json(resolved_report_root / "receipt.json", receipt)
    report_path = resolved_report_root / "REPORT.md"
    report_path.write_text(_report_text(receipt, result.trace), encoding="utf-8")
    receipt["trace_artifacts"]["report"] = {"path": "REPORT.md", "sha256": _sha256(report_path)}
    _write_json(resolved_report_root / "receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--run", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--singularityml-root", required=True, type=Path)
    parser.add_argument("--packet", type=Path, default=PACKET_PATH)
    parser.add_argument("--report-root", type=Path)
    arguments = parser.parse_args()
    packet = _load_json(arguments.packet)
    report_root = arguments.report_root or _default_report_root(packet)
    if arguments.run:
        receipt = run_packet(arguments.singularityml_root, report_root, arguments.packet)
        print(
            json.dumps(
                {
                    "packet_id": receipt["packet_id"],
                    "acceptance_passed": receipt["acceptance_passed"],
                    "learned_action_effect_count": receipt["learned_action_effect_count"],
                    "level_progress_observed": receipt["level_progress_observed"],
                    "report_root": str(report_root),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    with tempfile.TemporaryDirectory() as temporary_directory:
        reproduced_root = Path(temporary_directory)
        reproduced = run_packet(arguments.singularityml_root, reproduced_root, arguments.packet)
        reproduced_artifacts = _artifacts(reproduced_root)
    persisted = _load_json(report_root / "receipt.json")
    if persisted != reproduced:
        raise ValueError("persisted P0009 receipt does not reproduce exactly")
    if _artifacts(report_root) != reproduced_artifacts:
        raise ValueError("persisted P0009 artifacts do not reproduce exactly")
    print(f"{persisted['packet_id']}: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
