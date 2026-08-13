#!/usr/bin/env python3
"""Freeze a source-pinned ARC12 25+25 cohort from filenames only."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUSION_IMPORT = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_COHORT_IMPORT_001.json"
DEFAULT_SALT = "arc123-issue-2-fresh-frozen-self-mask-v1"
DEFAULT_ALLOCATION = {"evaluation": 12, "training": 13}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _git_output(source_root: Path, arguments: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _verify_clean_source(source_root: Path) -> str:
    if _git_output(source_root, ["status", "--porcelain"]):
        raise ValueError(f"source must remain clean/read-only: {source_root}")
    return _git_output(source_root, ["rev-parse", "HEAD"])


def _relative_repository_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("repository-relative paths may not escape the repository")
    return candidate


def _records_from_value(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    if isinstance(value, Mapping):
        return [
            item
            for benchmark_records in value.values()
            if isinstance(benchmark_records, list)
            for item in benchmark_records
            if isinstance(item, Mapping)
        ]
    return []


def _excluded_task_ids(imported: Mapping[str, Any]) -> set[str]:
    excluded: set[str] = set()
    for cohort_name in ("curated_60", "frozen_disjoint_50"):
        cohort = imported.get(cohort_name)
        if not isinstance(cohort, Mapping):
            continue
        for key in ("task_ids", "tasks"):
            for record in _records_from_value(cohort.get(key)):
                task_id = record.get("task_id")
                if isinstance(task_id, str) and task_id:
                    excluded.add(task_id)
    return excluded


def _filename_inventory(source_root: Path, benchmark: str) -> list[dict[str, str]]:
    task_root = source_root / "arc_data" / benchmark
    records: list[dict[str, str]] = []
    for split in ("evaluation", "training"):
        split_root = task_root / split
        if not split_root.is_dir():
            raise ValueError(f"source lacks expected split directory: {split_root}")
        for task_path in sorted(split_root.glob("*.json")):
            records.append(
                {
                    "benchmark": benchmark,
                    "split": split,
                    "task_id": task_path.stem,
                    "source_path": str(task_path),
                }
            )
    if not records:
        raise ValueError(f"source inventory is empty: {task_root}")
    return records


def _inventory_sha256(records: list[Mapping[str, str]]) -> str:
    canonical = "".join(
        f"{record['benchmark']}/{record['split']}/{record['task_id']}\n"
        for record in records
    )
    return _sha256_bytes(canonical.encode("utf-8"))


def _selection_hash(salt: str, record: Mapping[str, str]) -> str:
    return _sha256_bytes(
        f"{salt}:{record['benchmark']}:{record['split']}:{record['task_id']}".encode("utf-8")
    )


def _select_records(
    inventory: list[dict[str, str]],
    excluded_task_ids: set[str],
    salt: str,
    allocation: Mapping[str, int],
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for split, required_count in allocation.items():
        candidates = [record for record in inventory if record["split"] == split]
        candidates = [record for record in candidates if record["task_id"] not in excluded_task_ids]
        ranked = sorted(
            (
                {
                    **record,
                    "selection_hash": _selection_hash(salt, record),
                }
                for record in candidates
            ),
            key=lambda record: str(record["selection_hash"]),
        )
        if len(ranked) < required_count:
            raise ValueError(f"insufficient filename-only candidates for {split}")
        selected.extend(ranked[:required_count])
    return sorted(selected, key=lambda record: str(record["selection_hash"]))


def _manifest(
    arc1_source: Path,
    arc2_source: Path,
    arc1_repository: str,
    arc2_repository: str,
    exclusion_import: Path,
    salt: str,
) -> dict[str, Any]:
    imported = _load_json(exclusion_import)
    excluded_task_ids = _excluded_task_ids(imported)
    if not excluded_task_ids:
        raise ValueError("exclusion import does not provide prior ARC12 task IDs")
    source_roots = {"arc1": arc1_source, "arc2": arc2_source}
    repositories = {"arc1": arc1_repository, "arc2": arc2_repository}
    inventories = {
        benchmark: _filename_inventory(source_root, benchmark)
        for benchmark, source_root in source_roots.items()
    }
    source_pins = {
        benchmark: {
            "commit": _verify_clean_source(source_root),
            "repository": repositories[benchmark],
            "task_directory": f"arc_data/{benchmark}",
        }
        for benchmark, source_root in source_roots.items()
    }
    tasks: dict[str, list[dict[str, str]]] = {}
    inventory_metadata: dict[str, dict[str, Any]] = {}
    selected_task_ids = set(excluded_task_ids)
    for benchmark, inventory in inventories.items():
        excluded_count = len(selected_task_ids)
        selected = _select_records(inventory, selected_task_ids, salt, DEFAULT_ALLOCATION)
        selected_task_ids.update(record["task_id"] for record in selected)
        tasks[benchmark] = [
            {
                "benchmark": benchmark,
                "split": record["split"],
                "task_id": record["task_id"],
                "selection_hash": record["selection_hash"],
                "source_sha256": _sha256_bytes(Path(record["source_path"]).read_bytes()),
            }
            for record in selected
        ]
        inventory_metadata[benchmark] = {
            "inventory_count": len(inventory),
            "inventory_filename_sha256": _inventory_sha256(inventory),
            "excluded_prior_or_earlier_selection_task_id_count": excluded_count,
            "split_allocation": dict(DEFAULT_ALLOCATION),
        }
    if any(len(tasks[benchmark]) != sum(DEFAULT_ALLOCATION.values()) for benchmark in tasks):
        raise ValueError("frozen selection has the wrong per-benchmark task count")
    if len({record["task_id"] for records in tasks.values() for record in records}) != sum(
        len(records) for records in tasks.values()
    ):
        raise ValueError("frozen selection contains cross-benchmark duplicate task IDs")
    return {
        "schema_version": 1,
        "artifact_id": "ARC12-FILENAME-ONLY-FRESH-FROZEN-001",
        "title": "ARC12 Fresh Filename-Only Frozen 25+25 Cohort",
        "claim_boundary": "This cohort is frozen before any selected task is parsed, visualized, scored, or used for operator design. Selection reads only benchmark labels, split names, and filenames. Selected source JSON bytes are read only as opaque SHA-256 integrity commitments; their JSON content is not decoded by this freezer. The cohort excludes every task ID previously present in the imported curated-60 or frozen-disjoint-50 rosters, conservatively across both benchmarks, and prevents cross-benchmark duplicate IDs within this fresh cohort.",
        "live_controller_boundary": {
            "task_id_passed_to_agent": False,
            "cohort_metadata_passed_to_agent": False,
            "gt_feature_contract_passed_to_agent": False,
            "gt_solver_imported_or_called": False,
            "held_out_outputs_passed_to_agent": False,
        },
        "frozen_filename_only_50": {
            "task_count": 50,
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
                "prior_roster_import": {
                    "path": str(exclusion_import.relative_to(REPOSITORY_ROOT)),
                    "sha256": _sha256_bytes(exclusion_import.read_bytes()),
                    "excluded_task_id_count": len(excluded_task_ids),
                },
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
    parser.add_argument("--exclusion-import", type=Path, default=DEFAULT_EXCLUSION_IMPORT)
    parser.add_argument("--salt", default=DEFAULT_SALT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite frozen cohort: {output}")
    _write_json(
        output,
        _manifest(
            arguments.arc1_source,
            arguments.arc2_source,
            arguments.arc1_repository,
            arguments.arc2_repository,
            arguments.exclusion_import,
            arguments.salt,
        ),
    )
    print(f"frozen filename-only cohort written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
