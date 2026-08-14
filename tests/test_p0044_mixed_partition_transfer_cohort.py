from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_MIXED_PARTITION_TRANSFER_012.json"
P0042_COHORT_PATH = REPOSITORY_ROOT / "research" / "cohorts" / "ARC12_MIXED_PARTITION_DEVELOPMENT_011.json"
EXPECTED_COHORT_SHA256 = "28a3562f66495e2b8ba9e1c7de0d79a0706cc385588ff4f0fefc734fc791e9f6"


def _task_ids(payload: object) -> set[str]:
    if isinstance(payload, dict):
        task_id = payload.get("task_id")
        nested_ids = {task_id} if isinstance(task_id, str) and task_id else set()
        for value in payload.values():
            nested_ids.update(_task_ids(value))
        return nested_ids
    if isinstance(payload, list):
        nested_ids: set[str] = set()
        for value in payload:
            nested_ids.update(_task_ids(value))
        return nested_ids
    return set()


class P0044MixedPartitionTransferCohortTests(unittest.TestCase):
    def test_p0044_is_a_frozen_globally_disjoint_mixed_partition_transfer_roster(self) -> None:
        cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        p0042_cohort = json.loads(P0042_COHORT_PATH.read_text(encoding="utf-8"))
        entry = cohort["mixed_partition_transfer_40_p0044"]
        arc1_tasks = entry["tasks"]["arc1"]
        arc2_tasks = entry["tasks"]["arc2"]
        selected_task_ids = {task["task_id"] for task in [*arc1_tasks, *arc2_tasks]}
        imported_task_ids: set[str] = set()

        self.assertEqual(
            hashlib.sha256(COHORT_PATH.read_bytes()).hexdigest(),
            EXPECTED_COHORT_SHA256,
        )
        self.assertEqual(cohort["artifact_id"], "ARC12-MIXED-PARTITION-TRANSFER-012")
        self.assertIn("fresh transfer evidence", cohort["claim_boundary"])
        self.assertIn("non-comparable", cohort["claim_boundary"])
        self.assertEqual(entry["task_count"], 40)
        self.assertEqual(entry["per_benchmark_task_count"], 20)
        self.assertEqual(len(arc1_tasks), 20)
        self.assertEqual(len(arc2_tasks), 20)
        self.assertEqual({task["split"] for task in arc1_tasks}, {"evaluation"})
        self.assertEqual({task["split"] for task in arc2_tasks}, {"training"})
        self.assertEqual(len(selected_task_ids), 40)
        self.assertEqual(
            entry["selection_protocol"]["selection_salt"],
            "arc123-issue-2-p0044-mixed-partition-transfer-v1",
        )
        self.assertEqual(len(entry["selection_protocol"]["prior_roster_imports"]), 20)
        self.assertEqual(
            entry["selection_protocol"]["selection_metadata"]["arc1"][
                "excluded_prior_or_earlier_selection_task_id_count"
            ],
            938,
        )
        self.assertEqual(
            entry["selection_protocol"]["selection_metadata"]["arc2"][
                "excluded_prior_or_earlier_selection_task_id_count"
            ],
            958,
        )
        self.assertEqual(
            entry["source_pins"],
            p0042_cohort["mixed_partition_development_40_p0042"]["source_pins"],
        )
        self.assertTrue(
            all(value is False for value in cohort["live_controller_boundary"].values())
        )

        for imported in entry["selection_protocol"]["prior_roster_imports"]:
            import_path = REPOSITORY_ROOT / imported["path"]
            import_payload = json.loads(import_path.read_text(encoding="utf-8"))
            self.assertEqual(
                hashlib.sha256(import_path.read_bytes()).hexdigest(),
                imported["sha256"],
            )
            imported_task_ids.update(_task_ids(import_payload))

        self.assertEqual(len(imported_task_ids), 938)
        self.assertFalse(selected_task_ids & imported_task_ids)


if __name__ == "__main__":
    unittest.main()
