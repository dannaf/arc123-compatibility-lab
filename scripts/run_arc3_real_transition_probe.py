#!/usr/bin/env python3
"""Run or verify the source-pinned ARC3 shared-core real-transition probe."""

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

from arc123.adapters.arc3 import SourcePinnedARC3ReplayWorld
from arc123.controller import IterativeHypothesisLearner
from arc123.traces import render_arc3_transition_svg, render_trace_markdown


PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0004_ARC3_REAL_TRANSITION_PROBE.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifacts(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): _sha256(path)
        for path in sorted(root.glob("**/*"))
        if path.is_file()
    }


def _git_output(source_root: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_root), *arguments], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _verify_source_pin(source_root: Path, commit: str) -> None:
    resolved = _git_output(source_root, ["rev-parse", f"{commit}^{{commit}}"])
    if resolved != commit:
        raise ValueError("SingularityML source does not contain the requested immutable commit")


def _default_report_root(packet: Mapping[str, Any]) -> Path:
    raw_path = packet.get("report_root")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("packet lacks a repository-relative report_root")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("packet report root must remain inside this repository")
    return REPOSITORY_ROOT / relative


def _render_report(receipt: Mapping[str, Any], trace: Mapping[str, Any]) -> str:
    outcome = (
        "YES — SHARED-CORE TRANSITION HYPOTHESIS CONFIRMED"
        if receipt["external_probe_confirmed"]
        else "NO — SHARED-CORE TRANSITION HYPOTHESIS NOT CONFIRMED"
    )
    return "\n".join(
        [
            "# ARC3 `ls20` L1 Shared-Core Brain Surgery Report",
            "",
            f"## Outcome: {outcome}",
            "",
            f"- **Recorded public transitions consumed:** `{receipt['transition_count']}`",
            f"- **Initial learned-rule store:** `{receipt['initial_learned_store']}`",
            f"- **Final generic effect hypothesis:** `{receipt['selected_hypothesis']}`",
            f"- **Source commit:** `{receipt['source_pin']['commit']}`",
            "- **ARC3 level solved:** `NO CLAIM`",
            "",
            "## Boundary",
            "",
            "The live learner receives one current recorded public frame and its available actions. It never receives a post-hoc rule, oracle diff, reasoning annotation, future action sequence, or simulated outcome. The adapter refuses an action without a matching recorded transition instead of fabricating a state.",
            "",
            "## Corpus-Callosum Visualization",
            "",
            "![ARC3 real-transition corpus-callosum trace](corpus_callosum.svg)",
            "",
            "- Full explicit action/evidence/revision record: [`learning_trace.json`](learning_trace.json)",
            "",
            "## V&V",
            "",
            f"- Source-pinned public action trajectory: [{receipt['source_pin']['path']}]({receipt['source_pin']['url']})",
            f"- First deliberate probe accepted and changed state: `{receipt['transitions'][0]['accepted'] and receipt['transitions'][0]['changed'] is True}`",
            f"- Second exploit action accepted and changed state: `{receipt['transitions'][1]['accepted'] and receipt['transitions'][1]['changed'] is True}`",
            "- This verifies the shared observation/action/revision contract only; it is not a game-solving result.",
            "",
            render_trace_markdown(trace).rstrip(),
            "",
        ]
    )


def run_packet(
    singularityml_root: Path,
    report_root: Path | None = None,
    packet_path: Path = PACKET_PATH,
) -> dict[str, Any]:
    packet = _load_json(packet_path)
    source_pin = packet.get("source_pin")
    if not isinstance(source_pin, Mapping):
        raise ValueError("packet lacks a source pin")
    commit = str(source_pin["commit"])
    source_path = str(source_pin["path"])
    _verify_source_pin(singularityml_root, commit)
    report_root = report_root or _default_report_root(packet)
    world = SourcePinnedARC3ReplayWorld.from_git_source(
        singularityml_root,
        commit,
        source_path,
        source_repository=str(source_pin["repository"]),
        world_id="arc3-ls20-l1-public-replay",
    )
    result = IterativeHypothesisLearner().run_external_probe(world, packet["packet_id"])
    if len(result.transitions) != int(packet["controller"]["external_probe_count"]):
        raise ValueError("probe did not produce the pre-registered number of observed transitions")
    trace_path = report_root / "learning_trace.json"
    diagram_path = report_root / "corpus_callosum.svg"
    _write_json(trace_path, result.trace)
    before_frame = tuple(
        tuple(cell for cell in row)
        for row in result.transitions[0]["before"]["payload"]["frame"]
    )
    after_frame = tuple(
        tuple(cell for cell in row)
        for row in result.transitions[0]["after"]["payload"]["frame"]
    )
    render_arc3_transition_svg(diagram_path, before_frame, after_frame, result.trace)
    source_provenance = world.offline_provenance_for_report()
    receipt = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "claim_boundary": packet["claim_boundary"],
        "source_pin": source_provenance,
        "initial_learned_store": packet["controller"]["initial_learned_store"],
        "forbidden_live_inputs": packet["controller"]["forbidden_live_inputs"],
        "external_probe_confirmed": result.external_probe_confirmed,
        "transition_count": len(result.transitions),
        "selected_hypothesis": result.final_theory["name"],
        "final_theory": result.final_theory,
        "transitions": list(result.transitions),
        "trace_artifacts": {
            "learning_trace": {"path": "learning_trace.json", "sha256": _sha256(trace_path)},
            "corpus_callosum": {"path": "corpus_callosum.svg", "sha256": _sha256(diagram_path)},
        },
    }
    _write_json(report_root / "receipt.json", receipt)
    report_path = report_root / "REPORT.md"
    report_path.write_text(_render_report(receipt, result.trace), encoding="utf-8")
    receipt["trace_artifacts"]["report"] = {"path": "REPORT.md", "sha256": _sha256(report_path)}
    _write_json(report_root / "receipt.json", receipt)
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
                    "external_probe_confirmed": receipt["external_probe_confirmed"],
                    "transition_count": receipt["transition_count"],
                    "selected_hypothesis": receipt["selected_hypothesis"],
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
        raise ValueError("persisted ARC3 probe receipt does not reproduce exactly")
    if _artifacts(report_root) != reproduced_artifacts:
        raise ValueError("persisted ARC3 probe artifacts do not reproduce exactly")
    print(f"{persisted['packet_id']}: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
