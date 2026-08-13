#!/usr/bin/env python3
"""Freeze a source-pinned ARC12 development cohort from filenames only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import freeze_arc12_filename_holdout as freezer


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUSION_IMPORTS = (
    REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_COHORT_IMPORT_001.json",
    REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_FILENAME_HOLDOUT_001.json",
)
DEFAULT_SALT = "arc123-issue-2-band-axis-development-v1"
DEFAULT_ALLOCATION = {"evaluation": 10, "training": 10}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _task_records(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if isinstance(value.get("task_id"), str):
            yield value
        for nested in value.values():
            yield from _task_records(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _task_records(nested)


def _excluded_task_ids(import_paths: Iterable[Path]) -> tuple[set[str], list[dict[str, Any]]]:
    task_ids: set[str] = set()
    imports: list[dict[str, Any]] = []
    for path in import_paths:
        payload = freezer._load_json(path)
        imported_ids = {
            str(record["task_id"])
            for record in _task_records(payload)
            if isinstance(record.get("task_id"), str) and record["task_id"]
        }
        if not imported_ids:
            raise ValueError(f"exclusion import has no task IDs: {path}")
        task_ids.update(imported_ids)
        imports.append(
            {
                "path": str(path.relative_to(REPOSITORY_ROOT)),
                "sha256": _sha256(path),
                "excluded_task_id_count": len(imported_ids),
            }
        )
    return task_ids, imports


def _manifest(
    arc1_source: Path,
    arc2_source: Path,
    arc1_repository: str,
    arc2_repository: str,
    exclusion_imports: tuple[Path, ...],
    salt: str,
) -> dict[str, Any]:
    excluded_task_ids, import_metadata = _excluded_task_ids(exclusion_imports)
    source_roots = {"arc1": arc1_source, "arc2": arc2_source}
    repositories = {"arc1": arc1_repository, "arc2": arc2_repository}
    inventories = {
        benchmark: freezer._filename_inventory(source_root, benchmark)
        for benchmark, source_root in source_roots.items()
    }
    source_pins = {
        benchmark: {
            "commit": freezer._verify_clean_source(source_root),
            "repository": repositories[benchmark],
            "task_directory": f"arc_data/{benchmark}",
        }
        for benchmark, source_root in source_roots.items()
    }
    tasks: dict[str, list[dict[str, str]]] = {}
    selection_metadata: dict[str, dict[str, Any]] = {}
    selected_task_ids = set(excluded_task_ids)
    for benchmark, inventory in inventories.items():
        excluded_count = len(selected_task_ids)
        selected = freezer._select_records(
            inventory,
            selected_task_ids,
            salt,
            DEFAULT_ALLOCATION,
        )
        selected_task_ids.update(record["task_id"] for record in selected)
        tasks[benchmark] = [
            {
                "benchmark": benchmark,
                "split": record["split"],
                "task_id": record["task_id"],
                "selection_hash": record["selection_hash"],
                "source_sha256": hashlib.sha256(
                    Path(record["source_path"]).read_bytes()
                ).hexdigest(),
            }
            for record in selected
        ]
        selection_metadata[benchmark] = {
            "inventory_count": len(inventory),
            "inventory_filename_sha256": freezer._inventory_sha256(inventory),
            "excluded_prior_or_earlier_selection_task_id_count": excluded_count,
            "split_allocation": dict(DEFAULT_ALLOCATION),
        }
    if any(len(records) != sum(DEFAULT_ALLOCATION.values()) for records in tasks.values()):
        raise ValueError("development selection has wrong per-benchmark counts")
    selected_ids = [record["task_id"] for records in tasks.values() for record in records]
    if len(set(selected_ids)) != len(selected_ids):
        raise ValueError("development selection contains cross-benchmark duplicate task IDs")
    return {
        "schema_version": 1,
        "artifact_id": "ARC12-FILENAME-ONLY-DEVELOPMENT-001",
        "title": "ARC12 Fresh Filename-Only Development 20+20 Cohort",
        "claim_boundary": "This is a source-pinned development cohort selected only from benchmark labels, split names, and filenames before the next generic operator implementation is evaluated. It excludes all task IDs found in both the historical ARC12 import and the P0013 fresh frozen cohort, conservatively across benchmarks. Selected JSON bytes are read only as opaque source integrity checksums and are not decoded by this freezer. Any result is development evidence, not an independent generalization claim.",
        "live_controller_boundary": {
            "task_id_passed_to_agent": False,
            "cohort_metadata_passed_to_agent": False,
            "gt_feature_contract_passed_to_agent": False,
            "gt_solver_imported_or_called": False,
            "held_out_outputs_passed_to_agent": False,
        },
        "development_filename_only_40": {
            "task_count": 40,
            "per_benchmark_task_count": sum(DEFAULT_ALLOCATION.values()),
            "source_pins": source_pins,
            "selection_protocol": {
                "allowed_metadata": ["benchmark", "split", "task filename"],
                "opaque_integrity_recording": "selected source JSON bytes are hashed without decoding or inspecting grid semantics",
                "forbidden_inputs": [
                    "task grid semantics",
                    "held-out test output",
                    "GT feature manifest",
                    "GT solver code",
                    "historical decomposition",
                ],
                "method": "stratified sha256(salt:benchmark:split:task_id) rank over filenames",
                "selection_salt": salt,
                "prior_roster_imports": import_metadata,
                "selection_metadata": selection_metadata,
            },
            "tasks": tasks,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arc1-source", required=True, type=Path)
    parser.add_argument("--arc2-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--arc1-repository",
        default="https://github.com/dannaf/arc3-compatibility-lab-prime",
    )
    parser.add_argument(
        "--arc2-repository",
        default="https://github.com/dannaf/arc3-compatibility-lab-prime",
    )
    parser.add_argument("--salt", default=DEFAULT_SALT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite frozen development cohort: {output}")
    freezer._write_json(
        output,
        _manifest(
            arguments.arc1_source,
            arguments.arc2_source,
            arguments.arc1_repository,
            arguments.arc2_repository,
            DEFAULT_EXCLUSION_IMPORTS,
            arguments.salt,
        ),
    )
    print(f"filename-only development cohort written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
