from __future__ import annotations

import unittest

from arc123.arc3_mechanics import choose_goal_directed_action, learn_motion_model
from arc123.contracts import EnvironmentAction, EvidenceObservation, TransitionFeedback


def _frame(player_top: int, player_left: int) -> list[list[int]]:
    frame = [[0 for _ in range(16)] for _ in range(16)]
    frame[1][12] = 3
    for row in range(player_top, player_top + 2):
        for column in range(player_left, player_left + 2):
            frame[row][column] = 2
            frame[row + 2][column] = 3
    return frame


def _observation(step: int, frame: list[list[int]]) -> EvidenceObservation:
    return EvidenceObservation(
        observation_id=f"synthetic:step:{step}",
        world_id="synthetic-public-history",
        observation_kind="external_public_game_state",
        payload={
            "frame": frame,
            "available_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION4"],
            "levels_completed": 0,
        },
        metadata={"oracle_visible": False},
    )


def _feedback(
    step: int,
    action_key: str,
    before: list[list[int]],
    after: list[list[int]],
) -> TransitionFeedback:
    return TransitionFeedback(
        action=EnvironmentAction("external_key", {"key": action_key}),
        before=_observation(step, before),
        after=_observation(step + 1, after),
        accepted=True,
        changed=True,
        progress=0.0,
        terminal=False,
        metadata={"transition_source": "synthetic_public_history"},
    )


class ARC3MechanicsTests(unittest.TestCase):
    def test_public_history_learns_motion_without_assigning_unseen_actions_zero(self) -> None:
        history = (
            _feedback(0, "ACTION1", _frame(8, 4), _frame(7, 4)),
            _feedback(1, "ACTION2", _frame(7, 4), _frame(8, 4)),
            _feedback(2, "ACTION3", _frame(8, 4), _frame(8, 3)),
            _feedback(3, "ACTION4", _frame(8, 3), _frame(8, 4)),
        )
        model = learn_motion_model(history)
        current = _observation(4, _frame(8, 8))
        actions = tuple(
            EnvironmentAction("external_key", {"key": key})
            for key in ("ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5")
        )

        choice = choose_goal_directed_action(model, current, actions)

        self.assertEqual(model.effect_for("ACTION1").delta, (-1.0, 0.0))
        self.assertEqual(model.effect_for("ACTION2").delta, (1.0, 0.0))
        self.assertEqual(model.effect_for("ACTION3").delta, (0.0, -1.0))
        self.assertEqual(model.effect_for("ACTION4").delta, (0.0, 1.0))
        self.assertIsNone(model.effect_for("ACTION5"))
        self.assertTrue(model.as_dict()["unobserved_actions_remain_unknown"])
        self.assertIsNotNone(choice)
        self.assertEqual(choice.action.parameters["key"], "ACTION4")
        self.assertTrue(choice.is_non_default)
        self.assertLess(choice.goal_distance_after, choice.goal_distance_before)


if __name__ == "__main__":
    unittest.main()
