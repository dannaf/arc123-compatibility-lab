#!/usr/bin/env python3
"""Freeze a source-pinned mixed-partition ARC12 development cohort from filenames only."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

import freeze_arc12_filename_holdout as freezer


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUSION_IMPORT = (
    REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_COHORT_IMPORT_001.json"
)
DEFAULT_SALT = "arc123-post-p0041-mixed-partition-development-v1"
DEFAULT_ARTIFACT_ID = "ARC12-MIXED-PARTITION-DEVELOPMENT-001"
DEFAULT_TITLE = "ARC12 Filename-Only Mixed-Partition Development Cohort"
DEFAULT_COHORT_KEY = "mixed_partition_development_40"
DEFAULT_PER_BENCHMARK_TASK_COUNT = 20
DEFAULT_CLAIM_BOUNDARY = (
    "This mixed-partition development cohort is frozen before any selected task grid is "
    "parsed, visualized, scored, or used for operator design. Selection reads only benchmark "
    "labels, split names, and filenames. Selected source JSON bytes are read only as opaque "
    "SHA-256 integrity commitments; their JSON content is not decoded by this freezer. This "
    "protocol is explicitly non-comparable to prior all-training cohorts and must not be used "
    "for a benchmark submission claim."
)


def _source_pins(
    source_roots: Mapping[str, Path], repositories: Mapping[str, str]
) -> dict[str, dict[str, str]]:
    return {
        benchmark: {
            "commit": freezer._verify_clean_source(source_root),
            "repository": repositories[benchmark],
            "task_directory": f"arc_data/{benchmark}",
        }
        for benchmark, source_root in source_roots.items()
    }


def _manifest(
    arc1_source: Path,
    arc2_source: Path,
    arc1_repository: str,
    arc2_repository: str,
    exclusion_imports: tuple[Path, ...],
    salt: str,
    artifact_id: str,
    title: str,
    cohort_key: str,
    claim_boundary: str,
    split_by_benchmark: Mapping[str, str],
    per_benchmark_task_count: int,
) -> dict[str, Any]:
    if per_benchmark_task_count < 1:
        raise ValueError("per-benchmark task count must be positive")
    if set(split_by_benchmark) != {"arc1", "arc2"}:
        raise ValueError("mixed partition must declare exactly ARC1 and ARC2 splits")

    excluded_task_ids, import_metadata = freezer._excluded_task_ids_from_imports(
        exclusion_imports
    )
    source_roots = {"arc1": arc1_source, "arc2": arc2_source}
    repositories = {"arc1": arc1_repository, "arc2": arc2_repository}
    inventories = {
        benchmark: freezer._filename_inventory(source_root, benchmark)
        for benchmark, source_root in source_roots.items()
    }
    source_pins = _source_pins(source_roots, repositories)
    tasks: dict[str, list[dict[str, str]]] = {}
    inventory_metadata: dict[str, dict[str, Any]] = {}
    selected_task_ids = set(excluded_task_ids)

    for benchmark in ("arc1", "arc2"):
        inventory = inventories[benchmark]
        selected_split = split_by_benchmark[benchmark]
        allocation = {selected_split: per_benchmark_task_count}
        excluded_count = len(selected_task_ids)
        selected = freezer._select_records(
            inventory,
            selected_task_ids,
            salt,
            allocation,
        )
        selected_task_ids.update(record["task_id"] for record in selected)
        tasks[benchmark] = [
            {
                "benchmark": benchmark,
                "split": record["split"],
                "task_id": record["task_id"],
                "selection_hash": record["selection_hash"],
                "source_sha256": freezer._sha256_bytes(
                    Path(record["source_path"]).read_bytes()
                ),
            }
            for record in selected
        ]
        inventory_metadata[benchmark] = {
            "inventory_count": len(inventory),
            "inventory_filename_sha256": freezer._inventory_sha256(inventory),
            "excluded_prior_or_earlier_selection_task_id_count": excluded_count,
            "split_allocation": allocation,
        }

    if any(len(tasks[benchmark]) != per_benchmark_task_count for benchmark in tasks):
        raise ValueError("frozen selection has the wrong per-benchmark task count")
    selected_ids = {
        record["task_id"] for benchmark_tasks in tasks.values() for record in benchmark_tasks
    }
    if len(selected_ids) != sum(len(benchmark_tasks) for benchmark_tasks in tasks.values()):
        raise ValueError("frozen selection contains cross-benchmark duplicate task IDs")

    return {
        "schema_version": 1,
        "artifact_id": artifact_id,
        "title": title,
        "claim_boundary": claim_boundary,
        "live_controller_boundary": {
            "task_id_passed_to_agent": False,
            "cohort_metadata_passed_to_agent": False,
            "gt_feature_contract_passed_to_agent": False,
            "gt_solver_imported_or_called": False,
            "held_out_outputs_passed_to_agent": False,
        },
        cohort_key: {
            "task_count": sum(len(benchmark_tasks) for benchmark_tasks in tasks.values()),
            "per_benchmark_task_count": per_benchmark_task_count,
            "source_pins": source_pins,
            "selection_protocol": {
                "allowed_metadata": ["benchmark", "split", "task filename"],
                "opaque_integrity_recording": (
                    "selected source JSON bytes are hashed without decoding or inspecting "
                    "grid semantics"
                ),
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
                "selection_metadata": inventory_metadata,
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
    parser.add_argument(
        "--exclusion-import",
        type=Path,
        default=DEFAULT_EXCLUSION_IMPORT,
    )
    parser.add_argument(
        "--exclude-import",
        action="append",
        default=[],
        type=Path,
        help="Additional repository-relative frozen roster to exclude; may be repeated.",
    )
    parser.add_argument("--arc1-split", choices=("evaluation", "training"), default="evaluation")
    parser.add_argument("--arc2-split", choices=("evaluation", "training"), default="training")
    parser.add_argument(
        "--per-benchmark-task-count",
        type=int,
        default=DEFAULT_PER_BENCHMARK_TASK_COUNT,
    )
    parser.add_argument("--salt", default=DEFAULT_SALT)
    parser.add_argument("--artifact-id", default=DEFAULT_ARTIFACT_ID)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--cohort-key", default=DEFAULT_COHORT_KEY)
    parser.add_argument("--claim-boundary", default=DEFAULT_CLAIM_BOUNDARY)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite frozen cohort: {output}")
    if not arguments.artifact_id or not arguments.title or not arguments.cohort_key:
        raise ValueError("artifact ID, title, and cohort key must be non-empty")

    exclusion_imports = tuple(
        dict.fromkeys(
            [
                arguments.exclusion_import.resolve(),
                *(item.resolve() for item in arguments.exclude_import),
            ]
        )
    )
    manifest = _manifest(
        arguments.arc1_source.resolve(),
        arguments.arc2_source.resolve(),
        arguments.arc1_repository,
        arguments.arc2_repository,
        exclusion_imports,
        arguments.salt,
        arguments.artifact_id,
        arguments.title,
        arguments.cohort_key,
        arguments.claim_boundary,
        {"arc1": arguments.arc1_split, "arc2": arguments.arc2_split},
        arguments.per_benchmark_task_count,
    )
    freezer._write_json(output, manifest)
    print(f"frozen mixed-partition cohort written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
