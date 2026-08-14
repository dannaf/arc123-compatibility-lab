#!/usr/bin/env python3
"""Materialize or verify source-pinned offline ARC12 multistep annotations."""

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

from arc123.oracles import (
    build_arc12_ihl_gt_multistep,
    validate_arc12_ihl_gt_multistep,
)


PACKET_PATH = REPOSITORY_ROOT / "research" / "packets" / "P0010_ARC12_OFFLINE_MULTISTEP_ANNOTATIONS.json"


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


def _relative_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("P0010 output paths must remain inside the selected output root")
    return candidate


def _output_paths(packet: Mapping[str, Any], output_root: Path) -> tuple[Path, Path]:
    outputs = packet.get("outputs")
    if not isinstance(outputs, Mapping):
        raise ValueError("P0010 packet lacks output paths")
    materialization_path = outputs.get("materialization_path")
    report_root = outputs.get("report_root")
    if not isinstance(materialization_path, str) or not isinstance(report_root, str):
        raise ValueError("P0010 output paths are malformed")
    return output_root / _relative_path(materialization_path), output_root / _relative_path(report_root)


def _git_output(source_root: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _verify_source_pin(source_root: Path, source_pin: Mapping[str, Any]) -> None:
    commit = source_pin.get("commit")
    if not isinstance(commit, str) or not commit:
        raise ValueError("P0010 source pin lacks a commit")
    resolved = _git_output(source_root, ["rev-parse", f"{commit}^{{commit}}"])
    if resolved != commit:
        raise ValueError("P0010 source commit does not resolve exactly")


def _source_report_path(record: Mapping[str, Any]) -> Path:
    source = record.get("trajectory_source")
    if not isinstance(source, Mapping):
        raise ValueError("P0010 annotation record lacks trajectory source")
    trace = source.get("p0007_trace")
    if not isinstance(trace, Mapping) or not isinstance(trace.get("path"), str):
        raise ValueError("P0010 annotation record lacks source trace path")
    return Path(str(trace["path"])).parent / "REPORT.md"


def _task_report_text(record: Mapping[str, Any]) -> str:
    source = record["trajectory_source"]
    trace_source = source["p0007_trace"]
    diagram_source = source["p0007_corpus_callosum"]
    source_report = _source_report_path(record)
    source_report_under_reports = source_report.relative_to("reports")
    source_diagram_under_reports = Path(str(diagram_source["path"])).relative_to("reports")
    relative_source_report = Path("../../..") / source_report_under_reports
    relative_source_diagram = Path("../../..") / source_diagram_under_reports
    vv = record["final_program"]["post_answer_vv"]
    lines = [
        f"# {record['benchmark'].upper()} `{record['task_id']}` Offline Multistep Annotation",
        "",
        "## Outcome: YES — SOURCE TRACE HAS POST-ANSWER ALL-CELL V&V",
        "",
        f"- **Source trace:** [{trace_source['path']}]({trace_source['url']})",
        f"- **Source trace SHA-256:** `{trace_source['sha256']}`",
        f"- **Post-answer compared cells:** `{vv['compared_position_count']}`",
        f"- **Post-answer mismatched cells:** `{vv['mismatched_cell_count']}`",
        "- **Live ARC controller input:** `NO`",
        "- **ARC1/ARC2 solver claim:** `NO`",
        "",
        "## Source Corpus-Callosum Diagram",
        "",
        f"![P0007 source diagram]({relative_source_diagram.as_posix()})",
        "",
        f"- Full source brain-surgery report: [{source_report.as_posix()}]({relative_source_report.as_posix()})",
        "",
        "## Explicit Sequential Annotation",
        "",
        "These are deterministic structural projections of explicit source-trace events. They do not contain private chain-of-thought or an answer grid.",
        "",
    ]
    for step in record["steps"]:
        source_event = step["source_trace_event"]
        revision = step["revision"]
        lines.extend(
            [
                f"### `{step['step']}` — source `{source_event['step']}` `{source_event['action']}`",
                f"- **Offline hypothesis action:** `{step['hypothesis_action']}`",
                f"- **Revision kind:** `{revision['kind']}`",
                f"- **Counterexamples retained:** `{len(step['counterexamples'])}`",
                f"- **Source theory:** `{step['support']['theory_summary'].get('theory_id', 'not-applicable')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "The original live P0007 run had already committed its complete answer before post-answer V&V. This annotation is generated later from pinned public trace artifacts and is never available to the live learner or used as task dispatch.",
            "",
        ]
    )
    return "\n".join(lines)


def _readme_text(packet: Mapping[str, Any], payload: Mapping[str, Any], receipt: Mapping[str, Any]) -> str:
    lines = [
        "# P0010 ARC12 Offline Multistep Annotation Packet",
        "",
        "## Outcome: YES — THREE SOURCE-PINNED SEQUENTIAL ANNOTATIONS MATERIALIZED",
        "",
        f"- **Records:** `{payload['record_count']}`",
        f"- **Benchmarks:** `{receipt['annotation_summary']['benchmark_count']}`",
        f"- **Explicit annotation steps:** `{receipt['annotation_summary']['step_count']}`",
        f"- **Source P0007 commit:** `{payload['source_pin']['commit']}`",
        "- **Live ARC controller access:** `NO`",
        "- **General ARC solver claim:** `NO`",
        "",
        "## Boundary",
        "",
        "This is an offline research/V&V corpus. Each record is a deterministic structural projection of a published explicit P0007 trace. The annotation retains observations, hypotheses, counterexamples, residual-rule revisions, compositions, and final post-answer V&V without retaining a held-out answer grid or private chain-of-thought. It is not imported by the live ARC1/ARC2 controller.",
        "",
        "## Records",
        "",
    ]
    for record in payload["records"]:
        location = f"{record['benchmark']}/{record['task_id']}/REPORT.md"
        lines.append(
            f"- {record['benchmark'].upper()} `{record['task_id']}` — "
            f"[{location}]({location})"
        )
    lines.extend(
        [
            "",
            "## V&V",
            "",
            "- Packet source paths and SHA-256 values are checked before annotation projection.",
            "- `--verify` rebuilds the materialization and reports in a temporary directory, then compares every generated artifact hash.",
            "- The live-controller isolation suite rejects imports of offline materialization readers.",
            "",
        ]
    )
    return "\n".join(lines)


def _acceptance_passed(packet: Mapping[str, Any], summary: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    requirements = packet.get("acceptance")
    if not isinstance(requirements, Mapping):
        raise ValueError("P0010 packet lacks acceptance requirements")
    records = payload.get("records")
    if not isinstance(records, list):
        return False
    expected_actions = {
        "PROPOSE",
        "FIND_COUNTEREXAMPLE",
        "EXPLAIN_RESIDUAL",
        "COMPOSE_RULE",
        "COMMIT",
    }
    sequential = all(
        expected_actions
        <= {str(step["source_trace_event"]["action"]) for step in record["steps"]}
        and record["final_program"]["post_answer_vv"]["verdict"] == "YES"
        for record in records
    )
    no_live_access = all(
        value is False for value in payload["live_agent_boundary"].values()
    ) and all(record["live_agent_input"] is False for record in records)
    return bool(
        summary["record_count"] >= int(requirements["minimum_record_count"])
        and summary["benchmark_count"] >= int(requirements["minimum_benchmark_count"])
        and (
            not requirements["require_propose_counterexample_revision_compose_commit_sequence"]
            or sequential
        )
        and (
            not requirements["require_post_answer_yes_vv"]
            or all(record["final_program"]["post_answer_vv"]["verdict"] == "YES" for record in records)
        )
        and (not requirements["require_no_live_agent_access"] or no_live_access)
    )


def _generated_artifacts(output_root: Path, packet: Mapping[str, Any]) -> dict[str, str]:
    materialization_path, report_root = _output_paths(packet, output_root)
    files = [materialization_path, *sorted(path for path in report_root.glob("**/*") if path.is_file())]
    return {str(path.relative_to(output_root)): _sha256(path) for path in files}


def run_packet(
    source_root: Path,
    output_root: Path = REPOSITORY_ROOT,
    packet_path: Path = PACKET_PATH,
) -> dict[str, Any]:
    packet = _load_json(packet_path)
    if packet.get("external_mutation_allowed") is not False:
        raise ValueError("P0010 must forbid external repository mutation")
    if packet.get("benchmark_submission_allowed") is not False:
        raise ValueError("P0010 must forbid benchmark submission")
    source_pin = packet.get("source_pin")
    source_records = packet.get("source_records")
    if not isinstance(source_pin, Mapping) or not isinstance(source_records, list):
        raise ValueError("P0010 packet lacks its source pin or source records")
    _verify_source_pin(source_root, source_pin)
    materialization_path, report_root = _output_paths(packet, output_root)
    if materialization_path.exists() or (report_root.exists() and any(report_root.iterdir())):
        raise ValueError("P0010 refuses to overwrite existing materialization evidence")
    payload = build_arc12_ihl_gt_multistep(
        source_root,
        str(source_pin["commit"]),
        source_records,
        source_repository=str(source_pin["repository"]),
    )
    summary = validate_arc12_ihl_gt_multistep(payload)
    _write_json(materialization_path, payload)
    report_paths: dict[str, dict[str, str]] = {}
    for record in payload["records"]:
        report_path = report_root / record["benchmark"] / record["task_id"] / "REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_task_report_text(record), encoding="utf-8")
        report_paths[f"{record['benchmark']}/{record['task_id']}"] = {
            "path": str(report_path.relative_to(report_root)),
            "sha256": _sha256(report_path),
        }
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "packet_id": packet["packet_id"],
        "claim_boundary": packet["claim_boundary"],
        "source_pin": dict(source_pin),
        "selection_protocol": packet["selection_protocol"],
        "annotation_summary": summary,
        "live_agent_boundary": payload["live_agent_boundary"],
        "agent_input_contract": {
            "offline_annotations_passed_to_live_agent": False,
            "source_trace_passed_to_live_agent": False,
            "source_receipt_passed_to_live_agent": False,
            "held_out_answer_grid_passed_to_live_agent": False,
            "gt_solver_passed_to_live_agent": False,
        },
        "acceptance_requirements": dict(packet["acceptance"]),
        "artifact_paths": {
            "materialization": {
                "path": str(materialization_path.relative_to(output_root)),
                "sha256": _sha256(materialization_path),
            },
            "task_reports": report_paths,
        },
    }
    receipt["acceptance_passed"] = _acceptance_passed(packet, summary, payload)
    receipt_path = report_root / "receipt.json"
    _write_json(receipt_path, receipt)
    readme_path = report_root / "README.md"
    readme_path.write_text(_readme_text(packet, payload, receipt), encoding="utf-8")
    receipt["artifact_paths"]["receipt"] = {"path": "receipt.json", "sha256": _sha256(receipt_path)}
    receipt["artifact_paths"]["readme"] = {"path": "README.md", "sha256": _sha256(readme_path)}
    _write_json(receipt_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--run", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--packet", type=Path, default=PACKET_PATH)
    parser.add_argument("--output-root", type=Path, default=REPOSITORY_ROOT)
    arguments = parser.parse_args()
    if arguments.run:
        receipt = run_packet(arguments.source_root, arguments.output_root, arguments.packet)
        print(
            json.dumps(
                {
                    "packet_id": receipt["packet_id"],
                    "acceptance_passed": receipt["acceptance_passed"],
                    "annotation_summary": receipt["annotation_summary"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_root = Path(temporary_directory)
        reproduced = run_packet(arguments.source_root, temporary_root, arguments.packet)
        reproduced_artifacts = _generated_artifacts(temporary_root, _load_json(arguments.packet))
    persisted_root = arguments.output_root
    persisted_receipt = _load_json(
        _output_paths(_load_json(arguments.packet), persisted_root)[1] / "receipt.json"
    )
    if persisted_receipt != reproduced:
        raise ValueError("persisted P0010 receipt does not reproduce exactly")
    if _generated_artifacts(persisted_root, _load_json(arguments.packet)) != reproduced_artifacts:
        raise ValueError("persisted P0010 artifacts do not reproduce exactly")
    print(f"{persisted_receipt['packet_id']}: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
