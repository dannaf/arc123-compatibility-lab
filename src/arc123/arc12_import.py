"""Import ARC12 cohort metadata while quarantining historical schema oracle data."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


CURATED_NAME = "ARC12_CURATED_60_001.json"
FROZEN_NAME = "ARC12_FROZEN_DISJOINT_50_001.json"
OUTPUT_NAME = "ARC12_COHORT_IMPORT_001.json"


class ARC12ImportError(ValueError):
    """Raised when an ARC12 handoff cannot be imported without an oracle leak."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ARC12ImportError(f"cannot load {path}") from error
    if not isinstance(payload, dict):
        raise ARC12ImportError(f"{path} must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ARC12ImportError(f"cannot hash {path}") from error


def _git_output(repository_root: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository_root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ARC12ImportError(f"cannot inspect ARC12 source: {repository_root}") from error
    return result.stdout.strip()


def build_arc12_cohort_import(
    arc12_root: Path, expected_commit: str, source_repository: str
) -> dict[str, Any]:
    """Create a live-safe ARC12 cohort index from the verified handoff artifacts."""

    if _git_output(arc12_root, ["rev-parse", "HEAD"]) != expected_commit:
        raise ARC12ImportError("ARC12 source revision does not match the requested handoff pin")
    if _git_output(arc12_root, ["status", "--porcelain"]):
        raise ARC12ImportError("ARC12 source must be clean and read-only during import")
    export_root = arc12_root / "research" / "arc123_exports"
    curated_path = export_root / CURATED_NAME
    frozen_path = export_root / FROZEN_NAME
    curated = _load_json(curated_path)
    frozen = _load_json(frozen_path)
    tasks = curated.get("tasks")
    runtime_boundary = curated.get("runtime_boundary")
    if not isinstance(tasks, Mapping) or not isinstance(runtime_boundary, Mapping):
        raise ARC12ImportError("ARC12 curated export is malformed")
    if curated.get("task_count") != 60 or curated.get("task_counts") != {"arc1": 30, "arc2": 30}:
        raise ARC12ImportError("ARC12 curated export does not contain 60 tasks")
    if any(
        runtime_boundary.get(field_name) is not False
        for field_name in (
            "historical_schema_visible_to_live_agent",
            "feature_contract_visible_to_live_agent",
            "gt_solver_visible_to_live_agent",
            "held_out_test_output_visible_before_answer",
            "task_id_visible_to_live_agent",
        )
    ):
        raise ARC12ImportError("ARC12 curated export has an invalid live-agent boundary")
    task_ids: dict[str, list[dict[str, str]]] = {}
    for benchmark in ("arc1", "arc2"):
        benchmark_tasks = tasks.get(benchmark)
        if not isinstance(benchmark_tasks, list) or len(benchmark_tasks) != 30:
            raise ARC12ImportError(f"ARC12 curated export lacks 30 {benchmark} tasks")
        task_ids[benchmark] = []
        for task in benchmark_tasks:
            if not isinstance(task, Mapping):
                raise ARC12ImportError("ARC12 curated task is invalid")
            task_id = task.get("task_id")
            split = task.get("task_split")
            if not isinstance(task_id, str) or not isinstance(split, str):
                raise ARC12ImportError("ARC12 curated task lacks an ID or split")
            task_ids[benchmark].append({"task_id": task_id, "split": split})
    frozen_tasks = frozen.get("tasks")
    if not isinstance(frozen_tasks, Mapping) or frozen.get("task_count") != 50:
        raise ARC12ImportError("ARC12 frozen export does not contain 50 tasks")
    if frozen.get("curated_overlap_count") != 0:
        raise ARC12ImportError("ARC12 frozen export overlaps the curated curriculum")
    return {
        "schema_version": 1,
        "artifact_id": "ARC12-COHORT-IMPORT-001",
        "title": "Live-safe ARC12 curated/frozen cohort import for ARC123",
        "claim_boundary": (
            "This import exposes source-pinned task IDs, splits, and static-training "
            "world boundaries. It intentionally omits historical selected schemas, "
            "feature contracts, decomposition mappings, solver code, and held-out test "
            "outputs from the live controller input path."
        ),
        "upstream_handoff": {
            "repository": source_repository,
            "commit": expected_commit,
            "artifacts": {
                "curated": {
                    "path": f"research/arc123_exports/{CURATED_NAME}",
                    "sha256": _sha256(curated_path),
                    "url": f"{source_repository}/blob/{expected_commit}/research/arc123_exports/{CURATED_NAME}",
                },
                "frozen": {
                    "path": f"research/arc123_exports/{FROZEN_NAME}",
                    "sha256": _sha256(frozen_path),
                    "url": f"{source_repository}/blob/{expected_commit}/research/arc123_exports/{FROZEN_NAME}",
                },
            },
        },
        "live_controller_boundary": {
            "task_id_visible_to_controller": False,
            "historical_schema_visible_to_controller": False,
            "feature_contract_visible_to_controller": False,
            "decomposition_mapping_visible_to_controller": False,
            "gt_solver_visible_to_controller": False,
            "held_out_test_output_visible_before_commit": False,
        },
        "curated_60": {
            "source_pins": curated.get("source_pins"),
            "task_count": 60,
            "task_ids": task_ids,
        },
        "frozen_disjoint_50": {
            "source_pins": frozen.get("source_pins"),
            "selection_protocol": frozen.get("selection_protocol"),
            "task_count": 50,
            "tasks": frozen_tasks,
        },
    }


def write_arc12_cohort_import(
    arc12_root: Path,
    expected_commit: str,
    source_repository: str,
    output_path: Path,
) -> dict[str, Any]:
    payload = build_arc12_cohort_import(arc12_root, expected_commit, source_repository)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def validate_arc12_cohort_import(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    boundary = payload.get("live_controller_boundary")
    curated = payload.get("curated_60")
    frozen = payload.get("frozen_disjoint_50")
    if not isinstance(boundary, Mapping) or any(value is not False for value in boundary.values()):
        raise ARC12ImportError("ARC12 import weakens a controller boundary")
    if not isinstance(curated, Mapping) or curated.get("task_count") != 60:
        raise ARC12ImportError("ARC12 import has the wrong curated task count")
    if not isinstance(frozen, Mapping) or frozen.get("task_count") != 50:
        raise ARC12ImportError("ARC12 import has the wrong frozen task count")
    task_ids = curated.get("task_ids")
    frozen_tasks = frozen.get("tasks")
    if not isinstance(task_ids, Mapping) or not isinstance(frozen_tasks, Mapping):
        raise ARC12ImportError("ARC12 import lacks task lists")
    curated_pairs = {
        (benchmark, item.get("task_id"))
        for benchmark in ("arc1", "arc2")
        for item in task_ids.get(benchmark, [])
        if isinstance(item, Mapping)
    }
    frozen_pairs = {
        (benchmark, item.get("task_id"))
        for benchmark in ("arc1", "arc2")
        for item in frozen_tasks.get(benchmark, [])
        if isinstance(item, Mapping)
    }
    if len(curated_pairs) != 60 or len(frozen_pairs) != 50 or curated_pairs & frozen_pairs:
        raise ARC12ImportError("ARC12 import does not preserve disjoint cohort sizes")
    return {
        "curated_task_count": len(curated_pairs),
        "frozen_task_count": len(frozen_pairs),
        "live_controller_boundary": "pass",
    }
