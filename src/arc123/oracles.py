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
