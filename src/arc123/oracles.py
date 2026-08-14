"""Offline-only ARC12/ARC3 GT materialization and validation helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


ARC12_CURATED_PATH = "research/arc123_exports/ARC12_CURATED_60_001.json"
ARC12_DECOMPOSITION_PATH = "research/arc123_exports/ARC12_CURATED_60_DECOMPOSITIONS_001.json"
ARC3_AUDIT_PATH = "docs/ARC3_ORACLE_ASSET_AUDIT_001.json"


class OracleMaterializationError(ValueError):
    """Raised when an offline GT artifact is malformed or no longer source-pinned."""


def _git_show(repository_root: Path, commit: str, path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository_root), "show", f"{commit}:{path}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise OracleMaterializationError(f"cannot read source-pinned artifact {path}") from error
    return result.stdout


def _load_pinned_json(repository_root: Path, commit: str, path: str) -> tuple[dict[str, Any], str]:
    raw = _git_show(repository_root, commit, path)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise OracleMaterializationError(f"source-pinned artifact {path} is not JSON") from error
    if not isinstance(payload, dict):
        raise OracleMaterializationError(f"source-pinned artifact {path} must be a JSON object")
    return payload, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _selected_arc12_tasks(curated: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    tasks = curated.get("tasks")
    if not isinstance(tasks, Mapping):
        raise OracleMaterializationError("ARC12 curated source lacks tasks")
    selected: list[Mapping[str, Any]] = []
    for benchmark in ("arc1", "arc2"):
        candidates = tasks.get(benchmark)
        if not isinstance(candidates, list):
            raise OracleMaterializationError(f"ARC12 curated source lacks {benchmark} tasks")
        selected.extend(
            sorted(
                (candidate for candidate in candidates if isinstance(candidate, Mapping)),
                key=lambda candidate: str(candidate.get("task_id", "")),
            )[:2]
        )
    if len(selected) != 4:
        raise OracleMaterializationError("ARC12 GT pilot requires two records from each benchmark")
    return selected


def build_arc12_ihl_gt_pilot(
    arc12_root: Path,
    arc12_commit: str,
    *,
    source_repository: str = "https://github.com/dannaf/arc12-compatibility-lab",
) -> dict[str, Any]:
    """Build a four-task, source-pinned offline generic-decomposition pilot."""

    curated, curated_hash = _load_pinned_json(arc12_root, arc12_commit, ARC12_CURATED_PATH)
    decompositions, decomposition_hash = _load_pinned_json(
        arc12_root, arc12_commit, ARC12_DECOMPOSITION_PATH
    )
    mappings = decompositions.get("mappings")
    if not isinstance(mappings, list):
        raise OracleMaterializationError("ARC12 decomposition source lacks mappings")
    mapping_index = {
        (item.get("benchmark"), item.get("task_id")): item
        for item in mappings
        if isinstance(item, Mapping)
    }
    records: list[dict[str, Any]] = []
    for task in _selected_arc12_tasks(curated):
        benchmark = task.get("benchmark")
        task_id = task.get("task_id")
        if not isinstance(benchmark, str) or not isinstance(task_id, str):
            raise OracleMaterializationError("ARC12 curated pilot task lacks benchmark/task ID")
        decomposition = mapping_index.get((benchmark, task_id))
        if not isinstance(decomposition, Mapping):
            raise OracleMaterializationError(f"ARC12 decomposition missing for {benchmark}:{task_id}")
        generic_program = decomposition.get("proposed_generic_decomposition")
        provenance = task.get("source_provenance")
        historical_vv = task.get("historical_vv")
        if not isinstance(generic_program, Mapping) or not isinstance(provenance, Mapping):
            raise OracleMaterializationError(f"ARC12 pilot source record is malformed for {task_id}")
        records.append(
            {
                "record_id": f"ARC12-IHL-GT-PILOT-001:{benchmark}:{task_id}",
                "task_id": task_id,
                "benchmark": benchmark,
                "trajectory_source": {
                    "curated_record": {
                        "repository": source_repository,
                        "commit": arc12_commit,
                        "path": ARC12_CURATED_PATH,
                    },
                    "generic_decomposition": {
                        "repository": source_repository,
                        "commit": arc12_commit,
                        "path": ARC12_DECOMPOSITION_PATH,
                    },
                    "task_source": dict(provenance),
                },
                "offline_only": True,
                "live_agent_input": False,
                "steps": [
                    {
                        "step": 0,
                        "attention": {
                            "locus": "offline curated-record metadata and generic decomposition",
                            "purpose": "post-answer diagnostic comparison only",
                        },
                        "observation": {
                            "task_source_url": provenance.get("task_url"),
                            "perception_operators": generic_program.get("perception_operators", []),
                            "relation_operators": generic_program.get("relation_operators", []),
                        },
                        "hypothesis_action": "OFFLINE_GENERIC_DECOMPOSITION",
                        "hypothesis_before": None,
                        "hypothesis_after": {"candidate_generic_program": generic_program},
                        "predicted_scope": {
                            "coverage": "not a live prediction",
                            "boundary": "no held-out test cells or answer grid are materialized",
                        },
                        "prediction": {
                            "kind": "offline_generic_program_descriptor",
                            "answer_grid_included": False,
                        },
                        "support": {
                            "source_historical_vv": historical_vv,
                            "rediscovery_status": generic_program.get("rediscovery_status"),
                        },
                        "counterexamples": [],
                        "revision": {
                            "status": "not_applicable_to_post_hoc_seed_record",
                            "multiple_valid_trajectories_permitted": True,
                        },
                        "residual_summary": {
                            "status": "requires independent live learner comparison",
                            "live_controller_loaded": False,
                        },
                    }
                ],
                "verification": {
                    "source_pin_checked": True,
                    "source_historical_vv_present": isinstance(historical_vv, Mapping),
                    "hidden_chain_of_thought_present": False,
                    "held_out_test_output_before_commit_present": False,
                    "live_solver_dispatch_code_present": False,
                },
                "final_program": generic_program,
            }
        )
    return {
        "schema_version": 1,
        "artifact_id": "ARC12-IHL-GT-PILOT-001",
        "title": "Source-pinned ARC12 IHL GT pilot: externally reportable generic decompositions",
        "purpose": "Offline learner-development comparison and V&V only; never a live answer mechanism.",
        "schema_reference": "research/oracle_specs/ARC12_IHL_GT_SCHEMA_001.json",
        "source_pin": {
            "repository": source_repository,
            "commit": arc12_commit,
            "artifacts": {
                ARC12_CURATED_PATH: curated_hash,
                ARC12_DECOMPOSITION_PATH: decomposition_hash,
            },
        },
        "live_agent_boundary": {
            "records_visible_to_live_agent": False,
            "historical_schema_visible_to_live_agent": False,
            "generic_decomposition_visible_to_live_agent": False,
            "held_out_test_output_visible_before_commit": False,
            "gt_solver_visible_to_live_agent": False,
        },
        "selection_protocol": "two lexicographically first curated task IDs per benchmark; source metadata only",
        "record_count": len(records),
        "records": records,
    }


_ARC3_CLASSIFICATIONS = {
    "observable_human_action_trajectories": (
        "observable_real_action_trajectory",
        "usable as source-pinned external transition evidence; no hypothesis labels are imported",
        False,
    ),
    "segmented_human_level_trajectories": (
        "observable_real_action_trajectory",
        "usable as source-pinned per-level external transition evidence; add explicit public annotations only offline",
        True,
    ),
    "structured_reasoning_process_models": (
        "human_or_frontier_reasoning_annotation",
        "offline annotation provenance only; normalize only under an approved no-live-leak protocol",
        True,
    ),
    "observable_demo_commentary_transcripts": (
        "human_or_frontier_reasoning_annotation",
        "offline commentary provenance; requires explicit normalization before structured GT use",
        True,
    ),
    "offline_oracle_diffs": (
        "post_hoc_rule_oracle",
        "post-run comparison only; never initialize learner state",
        False,
    ),
    "offline_oracle_diff_reports": (
        "post_hoc_rule_oracle",
        "post-run human-readable comparison only; never initialize learner state",
        False,
    ),
    "offline_oracle_rule_phase_object_maps": (
        "post_hoc_rule_oracle",
        "post-run oracle comparison only; never initialize learner state",
        False,
    ),
    "brain_surgery_records": (
        "post_hoc_rule_oracle",
        "post-hoc debugging/visualization evidence; not a time-ordered live trajectory",
        True,
    ),
    "demo_video_media": (
        "video_only_commentary",
        "visual provenance only; requires transcription or explicit annotation before structured GT use",
        True,
    ),
    "oracle_isolation_guards": (
        "unsuitable_or_leaky_artifact",
        "boundary-control assets, not learning evidence; reuse only as test controls",
        False,
    ),
}


def build_arc3_ihl_gt_inventory(
    singularityml_root: Path,
    singularityml_commit: str,
    *,
    source_repository: str = "https://github.com/dannaf/SingularityML",
) -> dict[str, Any]:
    """Classify every source-pinned ARC3 audit entry without exposing it to a live run."""

    audit, audit_hash = _load_pinned_json(
        singularityml_root, singularityml_commit, ARC3_AUDIT_PATH
    )
    classes = audit.get("asset_classes")
    if not isinstance(classes, Mapping):
        raise OracleMaterializationError("ARC3 audit lacks asset classes")
    inventory: list[dict[str, Any]] = []
    for source_class, detail in sorted(classes.items()):
        if source_class not in _ARC3_CLASSIFICATIONS:
            raise OracleMaterializationError(f"ARC3 audit class has no required classification: {source_class}")
        if not isinstance(detail, Mapping):
            raise OracleMaterializationError("ARC3 audit class is malformed")
        classification, reuse_decision, new_annotation_required = _ARC3_CLASSIFICATIONS[source_class]
        entries = detail.get("entries")
        if not isinstance(entries, list):
            raise OracleMaterializationError(f"ARC3 audit class lacks entries: {source_class}")
        inventory.append(
            {
                "source_asset_class": source_class,
                "classification": classification,
                "entry_count": len(entries),
                "entries": [
                    {"path": item.get("path"), "sha256": item.get("sha256")}
                    for item in entries
                    if isinstance(item, Mapping)
                ],
                "audit_reuse_status": detail.get("reuse_status"),
                "audit_limitation": detail.get("limitation"),
                "reuse_decision": reuse_decision,
                "new_annotation_required": new_annotation_required,
                "live_learner_access": False,
            }
        )
    if any(item["entry_count"] != len(item["entries"]) for item in inventory):
        raise OracleMaterializationError("ARC3 audit has malformed individual asset entries")
    return {
        "schema_version": 1,
        "artifact_id": "ARC3-IHL-GT-INVENTORY-001",
        "title": "Source-pinned ARC3 artifact inventory for offline IHL GT work",
        "schema_reference": "research/oracle_specs/ARC3_IHL_GT_SCHEMA_001.json",
        "source_pin": {
            "repository": source_repository,
            "commit": singularityml_commit,
            "path": ARC3_AUDIT_PATH,
            "sha256": audit_hash,
            "url": f"{source_repository}/blob/{singularityml_commit}/{ARC3_AUDIT_PATH}",
        },
        "audited_asset_snapshot": {
            "repository": audit.get("source_repository"),
            "commit": audit.get("source_commit"),
            "role": "durable source snapshot used by the upstream audit entries",
        },
        "live_agent_boundary": {
            "inventory_visible_to_live_agent": False,
            "trajectory_oracle_visible_to_live_agent": False,
            "final_rule_visible_to_live_agent": False,
            "oracle_comparison_only_after_run": True,
        },
        "inventory_count": len(inventory),
        "asset_inventory": inventory,
        "reuse_vs_new_annotation_decision": {
            "directly_reusable_now": [
                "observable_real_action_trajectory as source-pinned replay environment evidence",
                "oracle_isolation_guards as boundary-test controls",
            ],
            "requires_new_or_approved_normalization": [
                "segmented trajectories need explicit public hypothesis/revision annotations",
                "reasoning and commentary records require offline-only normalization approval",
                "video media requires transcription or annotation",
            ],
            "validation_only": [
                "post-hoc rules, oracle diffs, and brain-surgery reports remain post-run comparisons",
            ],
        },
    }


def _forbidden_keys(value: Any, forbidden: set[str]) -> set[str]:
    if isinstance(value, Mapping):
        found = {str(key) for key in value if str(key) in forbidden}
        for child in value.values():
            found.update(_forbidden_keys(child, forbidden))
        return found
    if isinstance(value, list):
        found: set[str] = set()
        for child in value:
            found.update(_forbidden_keys(child, forbidden))
        return found
    return set()


def validate_arc12_ihl_gt_pilot(payload: Mapping[str, Any]) -> dict[str, int]:
    if payload.get("artifact_id") != "ARC12-IHL-GT-PILOT-001":
        raise OracleMaterializationError("wrong ARC12 GT pilot artifact ID")
    records = payload.get("records")
    if not isinstance(records, list) or payload.get("record_count") != len(records) or len(records) < 4:
        raise OracleMaterializationError("ARC12 GT pilot must retain its four selected records")
    forbidden = {
        "private_chain_of_thought",
        "held_out_test_output_before_commit",
        "live_solver_dispatch_code",
        "expected_output",
    }
    found = _forbidden_keys(payload, forbidden)
    if found:
        raise OracleMaterializationError(f"ARC12 GT pilot contains forbidden fields: {sorted(found)}")
    for record in records:
        if not isinstance(record, Mapping):
            raise OracleMaterializationError("ARC12 GT pilot record is malformed")
        for field in ("task_id", "benchmark", "trajectory_source", "steps", "verification"):
            if field not in record:
                raise OracleMaterializationError(f"ARC12 GT pilot record lacks {field}")
        if record.get("live_agent_input") is not False or record.get("offline_only") is not True:
            raise OracleMaterializationError("ARC12 GT pilot record weakens its live boundary")
        steps = record.get("steps")
        if not isinstance(steps, list) or not steps:
            raise OracleMaterializationError("ARC12 GT pilot record lacks externally reportable steps")
        for step in steps:
            if not isinstance(step, Mapping):
                raise OracleMaterializationError("ARC12 GT pilot step is malformed")
            for field in (
                "step",
                "attention",
                "observation",
                "hypothesis_action",
                "hypothesis_before",
                "hypothesis_after",
                "predicted_scope",
                "support",
                "counterexamples",
                "residual_summary",
            ):
                if field not in step:
                    raise OracleMaterializationError(f"ARC12 GT pilot step lacks {field}")
    return {"record_count": len(records), "benchmark_count": len({item["benchmark"] for item in records})}


_MULTISTEP_REQUIRED_ACTIONS = {
    "PROPOSE",
    "COMPARE",
    "FIND_COUNTEREXAMPLE",
    "EXPLAIN_RESIDUAL",
    "COMPOSE_RULE",
    "COMMIT",
}


def _pinned_json_record(
    source_root: Path,
    source_commit: str,
    source_record: Mapping[str, Any],
    *,
    path_field: str,
    hash_field: str,
) -> tuple[dict[str, Any], str, str]:
    raw_path = source_record.get(path_field)
    expected_hash = source_record.get(hash_field)
    if not isinstance(raw_path, str) or not isinstance(expected_hash, str):
        raise OracleMaterializationError(
            f"ARC12 multistep source record lacks {path_field}/{hash_field}"
        )
    raw = _git_show(source_root, source_commit, raw_path)
    actual_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if actual_hash != expected_hash:
        raise OracleMaterializationError(f"ARC12 multistep source hash changed: {raw_path}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise OracleMaterializationError(f"ARC12 multistep source is not JSON: {raw_path}") from error
    if not isinstance(payload, dict):
        raise OracleMaterializationError(f"ARC12 multistep source is not an object: {raw_path}")
    return payload, raw_path, actual_hash


def _trace_event_candidates(trace: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    events = trace.get("events")
    if not isinstance(events, list):
        raise OracleMaterializationError("ARC12 multistep source trace lacks events")
    validated = [event for event in events if isinstance(event, Mapping)]
    if len(validated) != len(events):
        raise OracleMaterializationError("ARC12 multistep source trace contains malformed events")
    if any(not isinstance(event.get("step"), int) or not isinstance(event.get("action"), str) for event in validated):
        raise OracleMaterializationError("ARC12 multistep source trace lacks explicit step/action fields")
    return sorted(validated, key=lambda event: int(event["step"]))


def _first_event(events: Sequence[Mapping[str, Any]], action: str) -> Mapping[str, Any] | None:
    return next((event for event in events if event["action"] == action), None)


def _last_event(events: Sequence[Mapping[str, Any]], action: str) -> Mapping[str, Any] | None:
    return next((event for event in reversed(events) if event["action"] == action), None)


def _milestone_events(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    milestones = [
        _first_event(events, "PROPOSE"),
        _first_event(events, "ATTEND"),
        _first_event(events, "COMPARE"),
        _first_event(events, "FIND_COUNTEREXAMPLE"),
        _first_event(events, "EXPLAIN_RESIDUAL"),
        _first_event(events, "COMPOSE_RULE"),
        _first_event(events, "ADD_RULE"),
        _first_event(events, "SPECIALIZE"),
        _last_event(events, "PROMOTE_CONSTRAINT"),
        _last_event(events, "COMMIT"),
    ]
    unique = {
        int(event["step"]): event
        for event in milestones
        if event is not None
    }
    selected = [unique[step] for step in sorted(unique)]
    selected_actions = {str(event["action"]) for event in selected}
    missing = _MULTISTEP_REQUIRED_ACTIONS - selected_actions
    if missing:
        raise OracleMaterializationError(
            f"ARC12 multistep source lacks required milestone actions: {sorted(missing)}"
        )
    return selected


def _mapping_subset(source: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    return {field: source[field] for field in fields if field in source}


def _rule_summary(raw_rule: Any) -> dict[str, Any] | None:
    if not isinstance(raw_rule, Mapping):
        return None
    return _mapping_subset(
        raw_rule,
        ("rule_id", "name", "operation", "parameters", "scope", "description_length"),
    )


def _counterexamples_from_event(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    direct = payload.get("counterexample") or payload.get("residual_counterexample")
    if isinstance(direct, Mapping):
        return [dict(direct)]
    support = payload.get("support")
    if isinstance(support, Mapping):
        counterexamples = support.get("counterexamples")
        if isinstance(counterexamples, list):
            return [dict(item) for item in counterexamples if isinstance(item, Mapping)][:1]
    return []


def _revision_summary(action: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    revision_kinds = {
        "FIND_COUNTEREXAMPLE": "counterexample_gate",
        "EXPLAIN_RESIDUAL": "residual_rule_addition",
        "ADD_RULE": "rule_addition",
        "SPECIALIZE": "scope_or_parameter_specialization",
        "COMPOSE_RULE": "ordered_rule_composition",
        "PROMOTE_CONSTRAINT": "training_compatibility_promotion",
    }
    summary: dict[str, Any] = {
        "kind": revision_kinds.get(action, "no_revision_at_this_milestone"),
        "derived_from_explicit_trace": True,
    }
    if action in {"EXPLAIN_RESIDUAL", "ADD_RULE"}:
        rule = _rule_summary(payload.get("added_rule") or payload.get("rule"))
        if rule is not None:
            summary["rule"] = rule
    if action == "COMPOSE_RULE":
        summary.update(_mapping_subset(payload, ("ordered_rule_ids",)))
    if action == "SPECIALIZE":
        summary.update(
            _mapping_subset(payload, ("from_value", "to_value", "parameter", "retained_rule_id"))
        )
    if action == "FIND_COUNTEREXAMPLE":
        summary.update(_mapping_subset(payload, ("causal_next_operation", "responsible_rule_id")))
    return summary


def _multistep_annotation_step(
    event: Mapping[str, Any],
    annotation_step: int,
) -> dict[str, Any]:
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise OracleMaterializationError("ARC12 multistep trace event lacks a payload object")
    action = str(event["action"])
    current_theory = payload.get("current_theory")
    theory_summary = (
        _mapping_subset(
            current_theory,
            (
                "theory_id",
                "parent_theory_id",
                "name",
                "rule_count",
                "contradiction_count",
                "matching_cell_count",
                "unknown_cell_count",
            ),
        )
        if isinstance(current_theory, Mapping)
        else {}
    )
    hypothesis_after = _mapping_subset(payload, ("theory_id", "parent_theory_id"))
    if theory_summary:
        hypothesis_after["theory"] = theory_summary
    rule = _rule_summary(payload.get("rule") or payload.get("added_rule"))
    if rule is not None:
        hypothesis_after["rule"] = rule
    hypothesis_after.update(_mapping_subset(payload, ("ordered_rule_ids",)))
    attention = _mapping_subset(payload, ("selected_demo", "selected_region", "reason"))
    attention["source_trace_action"] = action
    observation = _mapping_subset(payload, ("demo_index", "residual_cell_count", "explained_cell_count"))
    support = payload.get("support")
    if isinstance(support, Mapping):
        observation["compatibility"] = _mapping_subset(
            support,
            (
                "support_state",
                "exact_support_zero",
                "matching_cell_count",
                "contradiction_count",
                "unknown_cell_count",
            ),
        )
    return {
        "step": annotation_step,
        "source_trace_event": {"step": event["step"], "action": action},
        "attention": attention,
        "observation": observation,
        "hypothesis_action": f"OFFLINE_TRACE_{action}",
        "hypothesis_before": _mapping_subset(payload, ("parent_theory_id",)),
        "hypothesis_after": hypothesis_after,
        "predicted_scope": {
            "coverage": "source-pinned explicit trace milestone only",
            "boundary": "offline-only; no live task answer or held-out answer grid is materialized",
        },
        "prediction": {
            "kind": "post_hoc_explicit_trace_milestone",
            "answer_grid_included": False,
        },
        "support": {
            "source_trace_action": action,
            "source_trace_step": event["step"],
            "theory_summary": theory_summary,
        },
        "counterexamples": _counterexamples_from_event(payload),
        "revision": _revision_summary(action, payload),
        "residual_summary": _mapping_subset(
            payload,
            ("residual_cell_count", "explained_cell_count", "rule_count", "evaluated_demo_count", "status"),
        ),
        "rationale_annotation": {
            "construction": "deterministic structural projection of an explicit public trace event",
            "private_reasoning_included": False,
        },
    }


def _post_answer_vv_summary(receipt: Mapping[str, Any]) -> dict[str, Any]:
    test_cases = receipt.get("test_cases")
    cases = test_cases if isinstance(test_cases, list) else []
    compared = sum(
        int(case.get("compared_position_count", 0))
        for case in cases
        if isinstance(case, Mapping)
    )
    mismatched = sum(
        int(case.get("mismatched_cell_count", 0))
        for case in cases
        if isinstance(case, Mapping)
    )
    return {
        "verdict": "YES" if receipt.get("all_cells_match") is True else "NO",
        "all_cells_match": receipt.get("all_cells_match") is True,
        "training_exact": receipt.get("training_exact") is True,
        "compared_position_count": compared,
        "mismatched_cell_count": mismatched,
        "answer_grid_included": False,
    }


def build_arc12_ihl_gt_multistep(
    source_root: Path,
    source_commit: str,
    source_records: Sequence[Mapping[str, Any]],
    *,
    source_repository: str = "https://github.com/dannaf/arc123-compatibility-lab",
) -> dict[str, Any]:
    """Project audited P0007 public traces into offline-only sequential annotations."""

    records: list[dict[str, Any]] = []
    for source_record in source_records:
        if not isinstance(source_record, Mapping):
            raise OracleMaterializationError("ARC12 multistep source record is malformed")
        benchmark = source_record.get("benchmark")
        task_id = source_record.get("task_id")
        diagram_path = source_record.get("diagram_path")
        diagram_hash = source_record.get("diagram_sha256")
        if not all(
            isinstance(value, str) and value
            for value in (benchmark, task_id, diagram_path, diagram_hash)
        ):
            raise OracleMaterializationError("ARC12 multistep source record is incomplete")
        trace, trace_path, trace_hash = _pinned_json_record(
            source_root,
            source_commit,
            source_record,
            path_field="trace_path",
            hash_field="trace_sha256",
        )
        receipt, receipt_path, receipt_hash = _pinned_json_record(
            source_root,
            source_commit,
            source_record,
            path_field="receipt_path",
            hash_field="receipt_sha256",
        )
        raw_diagram = _git_show(source_root, source_commit, diagram_path)
        if hashlib.sha256(raw_diagram.encode("utf-8")).hexdigest() != diagram_hash:
            raise OracleMaterializationError(f"ARC12 multistep source hash changed: {diagram_path}")
        if receipt.get("benchmark") != benchmark or receipt.get("task_id") != task_id:
            raise OracleMaterializationError("ARC12 multistep trace/receipt task identity mismatch")
        if receipt.get("all_cells_match") is not True or receipt.get("training_exact") is not True:
            raise OracleMaterializationError("ARC12 multistep source must be an exact causal P0007 record")
        milestones = _milestone_events(_trace_event_candidates(trace))
        annotation_steps = [
            _multistep_annotation_step(event, annotation_step)
            for annotation_step, event in enumerate(milestones)
        ]
        final_event = milestones[-1]
        if final_event["action"] != "COMMIT":
            raise OracleMaterializationError("ARC12 multistep trajectory must end in a commit event")
        records.append(
            {
                "record_id": f"ARC12-IHL-GT-MULTISTEP-001:{benchmark}:{task_id}",
                "task_id": task_id,
                "benchmark": benchmark,
                "offline_only": True,
                "live_agent_input": False,
                "trajectory_source": {
                    "p0007_trace": {
                        "repository": source_repository,
                        "commit": source_commit,
                        "path": trace_path,
                        "sha256": trace_hash,
                        "url": f"{source_repository}/blob/{source_commit}/{trace_path}",
                    },
                    "p0007_receipt": {
                        "repository": source_repository,
                        "commit": source_commit,
                        "path": receipt_path,
                        "sha256": receipt_hash,
                        "url": f"{source_repository}/blob/{source_commit}/{receipt_path}",
                    },
                    "p0007_corpus_callosum": {
                        "repository": source_repository,
                        "commit": source_commit,
                        "path": diagram_path,
                        "sha256": diagram_hash,
                        "url": f"{source_repository}/blob/{source_commit}/{diagram_path}",
                    },
                    "task_source_url": receipt.get("source_task_url"),
                },
                "steps": annotation_steps,
                "final_program": {
                    "selected_hypothesis": receipt.get("selected_hypothesis"),
                    "source_commit_event_step": final_event["step"],
                    "post_answer_vv": _post_answer_vv_summary(receipt),
                },
                "verification": {
                    "source_pin_checked": True,
                    "source_trace_hash_checked": True,
                    "source_receipt_hash_checked": True,
                    "source_diagram_hash_checked": True,
                    "explicit_step_order_checked": True,
                    "hidden_chain_of_thought_present": False,
                    "held_out_test_output_before_commit_present": False,
                    "live_solver_dispatch_code_present": False,
                },
            }
        )
    return {
        "schema_version": 1,
        "artifact_id": "ARC12-IHL-GT-MULTISTEP-001",
        "title": "Source-pinned ARC12 IHL GT: explicit offline multistep trace annotations",
        "purpose": (
            "Offline learner-development comparison and V&V only; deterministic projections of "
            "published explicit traces, never a live answer mechanism."
        ),
        "schema_reference": "research/oracle_specs/ARC12_IHL_GT_MULTISTEP_SCHEMA_001.json",
        "source_pin": {"repository": source_repository, "commit": source_commit},
        "selection_protocol": (
            "all P0007 records pre-declared in the packet that are exact with causal-trace "
            "acceptance; no additional task selection after materialization"
        ),
        "live_agent_boundary": {
            "records_visible_to_live_agent": False,
            "source_trace_visible_to_live_agent": False,
            "source_receipt_visible_to_live_agent": False,
            "source_diagram_visible_to_live_agent": False,
            "annotation_visible_to_live_agent": False,
            "held_out_answer_grid_visible_before_commit": False,
            "gt_solver_visible_to_live_agent": False,
        },
        "record_count": len(records),
        "records": records,
    }


def validate_arc12_ihl_gt_multistep(payload: Mapping[str, Any]) -> dict[str, int]:
    """Validate the stricter sequential/offline contract for multistep annotations."""

    if payload.get("artifact_id") != "ARC12-IHL-GT-MULTISTEP-001":
        raise OracleMaterializationError("wrong ARC12 multistep artifact ID")
    records = payload.get("records")
    if not isinstance(records, list) or payload.get("record_count") != len(records) or len(records) < 3:
        raise OracleMaterializationError("ARC12 multistep artifact requires at least three records")
    forbidden = {
        "private_chain_of_thought",
        "held_out_test_output_before_commit",
        "live_solver_dispatch_code",
        "expected_output",
    }
    found = _forbidden_keys(payload, forbidden)
    if found:
        raise OracleMaterializationError(
            f"ARC12 multistep artifact contains forbidden fields: {sorted(found)}"
        )
    boundary = payload.get("live_agent_boundary")
    if not isinstance(boundary, Mapping) or any(value is not False for value in boundary.values()):
        raise OracleMaterializationError("ARC12 multistep artifact weakens the live-agent boundary")
    total_steps = 0
    benchmarks: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise OracleMaterializationError("ARC12 multistep record is malformed")
        benchmark = record.get("benchmark")
        if not isinstance(benchmark, str):
            raise OracleMaterializationError("ARC12 multistep record lacks a benchmark")
        benchmarks.add(benchmark)
        if record.get("offline_only") is not True or record.get("live_agent_input") is not False:
            raise OracleMaterializationError("ARC12 multistep record weakens its live boundary")
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) < 7:
            raise OracleMaterializationError("ARC12 multistep record lacks a substantive sequence")
        source_steps: list[int] = []
        actions: set[str] = set()
        for expected_step, step in enumerate(steps):
            if not isinstance(step, Mapping) or step.get("step") != expected_step:
                raise OracleMaterializationError("ARC12 multistep annotation steps are not contiguous")
            source_event = step.get("source_trace_event")
            if not isinstance(source_event, Mapping):
                raise OracleMaterializationError("ARC12 multistep step lacks a source event reference")
            source_step = source_event.get("step")
            action = source_event.get("action")
            if not isinstance(source_step, int) or not isinstance(action, str):
                raise OracleMaterializationError("ARC12 multistep source event reference is malformed")
            source_steps.append(source_step)
            actions.add(action)
            for field in (
                "attention",
                "observation",
                "hypothesis_action",
                "hypothesis_before",
                "hypothesis_after",
                "predicted_scope",
                "prediction",
                "support",
                "counterexamples",
                "revision",
                "residual_summary",
            ):
                if field not in step:
                    raise OracleMaterializationError(f"ARC12 multistep step lacks {field}")
            prediction = step.get("prediction")
            if not isinstance(prediction, Mapping) or prediction.get("answer_grid_included") is not False:
                raise OracleMaterializationError("ARC12 multistep step includes an answer grid")
        if source_steps != sorted(source_steps) or len(set(source_steps)) != len(source_steps):
            raise OracleMaterializationError("ARC12 multistep event order is not strictly increasing")
        missing_actions = _MULTISTEP_REQUIRED_ACTIONS - actions
        if missing_actions:
            raise OracleMaterializationError(
                f"ARC12 multistep record lacks sequential actions: {sorted(missing_actions)}"
            )
        final_program = record.get("final_program")
        if not isinstance(final_program, Mapping):
            raise OracleMaterializationError("ARC12 multistep record lacks final post-answer V&V")
        vv = final_program.get("post_answer_vv")
        if not isinstance(vv, Mapping) or vv.get("verdict") != "YES" or vv.get("answer_grid_included") is not False:
            raise OracleMaterializationError("ARC12 multistep post-answer V&V is invalid")
        verification = record.get("verification")
        if not isinstance(verification, Mapping) or any(
            verification.get(field) is not False
            for field in (
                "hidden_chain_of_thought_present",
                "held_out_test_output_before_commit_present",
                "live_solver_dispatch_code_present",
            )
        ):
            raise OracleMaterializationError("ARC12 multistep verification weakens isolation")
        total_steps += len(steps)
    if len(benchmarks) < 2:
        raise OracleMaterializationError("ARC12 multistep artifact must cover both ARC1 and ARC2")
    return {"record_count": len(records), "benchmark_count": len(benchmarks), "step_count": total_steps}


def validate_arc3_ihl_gt_inventory(payload: Mapping[str, Any]) -> dict[str, int]:
    if payload.get("artifact_id") != "ARC3-IHL-GT-INVENTORY-001":
        raise OracleMaterializationError("wrong ARC3 GT inventory artifact ID")
    inventory = payload.get("asset_inventory")
    if not isinstance(inventory, list) or payload.get("inventory_count") != len(inventory):
        raise OracleMaterializationError("ARC3 inventory count does not match its entries")
    classes = {
        "observable_real_action_trajectory",
        "human_or_frontier_reasoning_annotation",
        "post_hoc_rule_oracle",
        "video_only_commentary",
        "unsuitable_or_leaky_artifact",
    }
    observed_classes: set[str] = set()
    for item in inventory:
        if not isinstance(item, Mapping):
            raise OracleMaterializationError("ARC3 inventory item is malformed")
        classification = item.get("classification")
        if classification not in classes:
            raise OracleMaterializationError("ARC3 inventory has an unknown classification")
        observed_classes.add(str(classification))
        entries = item.get("entries")
        if not isinstance(entries, list) or item.get("entry_count") != len(entries):
            raise OracleMaterializationError("ARC3 inventory does not retain every audited entry")
        if item.get("live_learner_access") is not False:
            raise OracleMaterializationError("ARC3 inventory weakens live oracle isolation")
    if observed_classes != classes:
        raise OracleMaterializationError("ARC3 inventory does not cover every required classification")
    boundary = payload.get("live_agent_boundary")
    if not isinstance(boundary, Mapping) or boundary.get("oracle_comparison_only_after_run") is not True:
        raise OracleMaterializationError("ARC3 inventory lacks post-run oracle isolation")
    asset_snapshot = payload.get("audited_asset_snapshot")
    if not isinstance(asset_snapshot, Mapping) or not isinstance(asset_snapshot.get("commit"), str):
        raise OracleMaterializationError("ARC3 inventory lacks the audited underlying asset pin")
    return {
        "inventory_count": len(inventory),
        "classification_count": len(observed_classes),
        "asset_count": sum(int(item["entry_count"]) for item in inventory),
    }


def materialize_oracle_lane(
    arc12_root: Path,
    arc12_commit: str,
    singularityml_root: Path,
    singularityml_commit: str,
    output_root: Path,
) -> dict[str, Any]:
    """Write and validate the two offline artifacts from immutable source trees."""

    arc12_payload = build_arc12_ihl_gt_pilot(arc12_root, arc12_commit)
    arc3_payload = build_arc3_ihl_gt_inventory(singularityml_root, singularityml_commit)
    arc12_path = output_root / "ARC12_IHL_GT_PILOT_001.json"
    arc3_path = output_root / "ARC3_IHL_GT_INVENTORY_001.json"
    _write_json(arc12_path, arc12_payload)
    _write_json(arc3_path, arc3_payload)
    return {
        "arc12": validate_arc12_ihl_gt_pilot(arc12_payload),
        "arc3": validate_arc3_ihl_gt_inventory(arc3_payload),
        "outputs": {"arc12": str(arc12_path), "arc3": str(arc3_path)},
    }
