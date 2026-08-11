from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.adapters.arc3 import SourcePinnedARC3ReplayWorld
from arc123.contracts import EnvironmentAction
from arc123.controller import IterativeHypothesisLearner
from arc123.isolation import OracleIsolationError
from arc123.model import ActionKind


SOURCE_COMMIT = "a" * 40
SOURCE_PATH = "demos/human_play/segmented/public_level.jsonl"


def _public_transition_jsonl() -> str:
    records = [
        {
            "step": 0,
            "action": "RESET",
            "available": ["ACTION1", "ACTION2"],
            "frame": [[0, 0], [0, 1]],
            "score": 0,
            "levels_completed": 0,
            "state": "GameState.NOT_FINISHED",
            "changed": True,
        },
        {
            "step": 1,
            "action": "ACTION1",
            "available": ["ACTION1", "ACTION2"],
            "frame": [[0, 0], [1, 0]],
            "score": 0,
            "levels_completed": 0,
            "state": "GameState.NOT_FINISHED",
            "changed": True,
        },
        {
            "step": 2,
            "action": "ACTION1",
            "available": ["ACTION1", "ACTION2"],
            "frame": [[1, 0], [0, 0]],
            "score": 0,
            "levels_completed": 0,
            "state": "GameState.NOT_FINISHED",
            "changed": True,
        },
    ]
    return "\n".join(json.dumps(record) for record in records) + "\n"


class SharedARC3ContractTests(unittest.TestCase):
    def _world(self) -> SourcePinnedARC3ReplayWorld:
        with patch(
            "arc123.adapters.arc3._git_output",
            side_effect=[SOURCE_COMMIT, _public_transition_jsonl()],
        ):
            return SourcePinnedARC3ReplayWorld.from_git_source(
                Path("/source"), SOURCE_COMMIT, SOURCE_PATH
            )

    def test_arc12_static_evidence_uses_the_neutral_observation_action_contract(self) -> None:
        environment = ARC12InteractiveEnv.from_task_payload(
            {
                "train": [{"input": [[1]], "output": [[2]]}],
                "test": [{"input": [[1]], "output": [[2]]}],
            }
        )

        world = environment.observe()
        self.assertEqual(world.observation_kind, "static_training_world")
        self.assertFalse(world.payload["test_targets_visible"])
        feedback = environment.act(environment.available_actions()[0])
        self.assertTrue(feedback.accepted)
        self.assertEqual(feedback.after.observation_kind, "training_pair")
        self.assertNotIn("expected_output", feedback.after.payload)

    def test_arc3_replay_exposes_only_current_observable_state_and_refuses_simulation(self) -> None:
        world = self._world()
        view = world.agent_view()
        serialized_view = json.dumps(view, sort_keys=True)
        self.assertNotIn(SOURCE_PATH, serialized_view)
        self.assertNotIn(SOURCE_COMMIT, serialized_view)
        self.assertFalse(view["metadata"]["oracle_visible"])
        self.assertEqual([action.parameters["key"] for action in world.available_actions()], ["ACTION1", "ACTION2"])

        refused = world.act(EnvironmentAction("external_key", {"key": "ACTION2"}))
        self.assertFalse(refused.accepted)
        self.assertIn("no state was simulated", refused.metadata["reason"])
        self.assertEqual(world.observe().observation_id, "arc3-public-replay:step:0")

    def test_shared_learner_revises_on_a_real_transition_contract(self) -> None:
        world = self._world()
        result = IterativeHypothesisLearner().run_external_probe(world, "shared-arc3")

        self.assertTrue(result.external_probe_confirmed)
        self.assertEqual(len(result.transitions), 2)
        self.assertEqual(
            result.final_theory["rules"][0]["operation"], "environment_transition"
        )
        self.assertEqual(
            result.final_theory["rules"][0]["parameters"]["effect"], "state_change_possible"
        )
        actions = [event["action"] for event in result.trace["events"]]
        self.assertEqual(
            actions,
            [
                ActionKind.ATTEND.value,
                ActionKind.PROPOSE.value,
                ActionKind.APPLY_LOCALLY.value,
                ActionKind.COMPARE.value,
                ActionKind.FIND_COUNTEREXAMPLE.value,
                ActionKind.SPECIALIZE.value,
                ActionKind.BIND_PARAMETER.value,
                ActionKind.APPLY_LOCALLY.value,
                ActionKind.COMPARE.value,
                ActionKind.PROMOTE_CONSTRAINT.value,
                ActionKind.COMMIT.value,
            ],
        )

    def test_live_arc3_adapter_rejects_oracle_and_final_rule_paths(self) -> None:
        with self.assertRaises(OracleIsolationError):
            SourcePinnedARC3ReplayWorld.from_git_source(
                Path("/source"),
                SOURCE_COMMIT,
                "reports/real_games/ls20/offline_oracle_diff.json",
            )
        with self.assertRaises(OracleIsolationError):
            SourcePinnedARC3ReplayWorld.from_git_source(
                Path("/source"),
                SOURCE_COMMIT,
                "demos/human_play/segmented/final_rule.jsonl",
            )


if __name__ == "__main__":
    unittest.main()
