from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.model import ActionKind
from arc123.theory import ScopePredicate


class PartialTheoryRevisionTests(unittest.TestCase):
    def _scope_environment(self) -> ARC12InteractiveEnv:
        return ARC12InteractiveEnv.from_task_payload(
            {
                "train": [
                    {
                        "input": [[1, 0, 2], [0, 0, 0], [0, 0, 0]],
                        "output": [[0, 0, 2], [0, 0, 0], [0, 0, 1]],
                    },
                    {
                        "input": [[0, 1, 0], [2, 0, 0], [0, 0, 0]],
                        "output": [[0, 0, 0], [2, 0, 0], [0, 1, 0]],
                    },
                ],
                "test": [
                    {
                        "input": [[1, 0, 3], [0, 0, 0], [0, 0, 0]],
                        "output": [[0, 0, 3], [0, 0, 0], [0, 0, 1]],
                    }
                ],
            }
        )

    def _two_rule_environment(self) -> ARC12InteractiveEnv:
        return ARC12InteractiveEnv.from_task_payload(
            {
                "train": [
                    {
                        "input": [
                            [1, 0, 0, 2],
                            [0, 3, 0, 0],
                            [0, 0, 0, 0],
                            [0, 0, 0, 0],
                        ],
                        "output": [
                            [0, 0, 0, 0],
                            [0, 3, 0, 0],
                            [0, 0, 0, 0],
                            [2, 0, 0, 1],
                        ],
                    },
                    {
                        "input": [
                            [0, 1, 2, 0],
                            [0, 0, 0, 0],
                            [0, 0, 3, 0],
                            [0, 0, 0, 0],
                        ],
                        "output": [
                            [0, 0, 0, 0],
                            [0, 0, 0, 0],
                            [0, 0, 3, 0],
                            [0, 2, 1, 0],
                        ],
                    },
                ],
                "test": [
                    {
                        "input": [
                            [1, 0, 0, 2],
                            [0, 0, 0, 0],
                            [0, 3, 0, 0],
                            [0, 0, 0, 0],
                        ],
                        "output": [
                            [0, 0, 0, 0],
                            [0, 0, 0, 0],
                            [0, 3, 0, 0],
                            [2, 0, 0, 1],
                        ],
                    }
                ],
            }
        )

    def _learner(self) -> IterativeHypothesisLearner:
        return IterativeHypothesisLearner(
            operator_families=("scoped_coordinate_transform",),
            beam_width=32,
            max_revisions=256,
        )

    def test_counterexample_changes_a_retained_rule_scope(self) -> None:
        environment = self._scope_environment()
        result = self._learner().solve(environment, "scope-revision")

        self.assertTrue(result.training_exact)
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        self.assertIsNotNone(result.final_theory)
        rules = result.final_theory["rules"]
        self.assertEqual(rules[1]["rule_id"], "coordinate-rotate_180")
        self.assertEqual(rules[1]["scope"], {"kind": "color_equals", "value": 1})
        history = result.final_theory["history"]
        self.assertTrue(
            any(
                action["kind"] == ActionKind.SPECIALIZE.value
                and action["target"] == "coordinate-rotate_180"
                and action["parameters"]["retained_rule_id"] == "coordinate-rotate_180"
                for action in history
            )
        )
        events = result.trace["events"]
        counterexample_step = next(
            event["step"]
            for event in events
            if event["action"] == ActionKind.FIND_COUNTEREXAMPLE.value
            and event["payload"]["responsible_rule"]["name"] == "rotate_180(scope=all)"
        )
        scope_change = next(
            event
            for event in events
            if event["action"] == ActionKind.CHANGE_SCOPE.value
            and event["payload"]["to_scope"] == {"kind": "color_equals", "value": 1}
        )
        self.assertGreater(scope_change["step"], counterexample_step)
        self.assertEqual(
            scope_change["payload"]["from_scope"], {"kind": "all", "value": None}
        )

    def test_residual_adds_a_second_ordered_rule_without_dropping_the_first(self) -> None:
        environment = self._two_rule_environment()
        result = self._learner().solve(environment, "two-rule-composition")

        self.assertTrue(result.training_exact)
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        self.assertIsNotNone(result.final_theory)
        rules = result.final_theory["rules"]
        self.assertEqual([rule["operation"] for rule in rules], [
            "identity",
            "coordinate_transform",
            "coordinate_transform",
        ])
        self.assertEqual(
            {rule["scope"]["value"] for rule in rules[1:]}, {1, 2}
        )
        composition_events = [
            event
            for event in result.trace["events"]
            if event["action"] == ActionKind.COMPOSE_RULE.value
            and len(event["payload"]["ordered_rule_ids"]) == 3
        ]
        self.assertTrue(composition_events)
        self.assertEqual(
            composition_events[0]["payload"]["ordered_rule_ids"][1], "coordinate-rotate_180"
        )

    def test_second_demo_is_selected_after_a_surviving_partial_theory(self) -> None:
        result = self._learner().solve(self._scope_environment(), "dynamic-attention")

        discriminating_attention = [
            event["payload"]
            for event in result.trace["events"]
            if event["action"] == ActionKind.CHOOSE_NEXT_DEMO.value
            and event["payload"]["selection_basis"]
            == "unseen_demo_selected_for_residual_version_space_discrimination"
        ]
        self.assertTrue(discriminating_attention)
        self.assertTrue(
            any(
                payload["selected_demo"] == 1
                and payload["previously_observed_demos"] == [0]
                for payload in discriminating_attention
            )
        )

    def test_generic_component_and_border_scope_predicates_are_input_derived(self) -> None:
        grid = ((1, 1, 0), (1, 0, 2), (0, 2, 2))
        from arc123.theory import _component_context

        context = _component_context(grid)
        self.assertTrue(ScopePredicate("component_area_equals", 3).matches(grid, 0, 0, context))
        self.assertFalse(ScopePredicate("component_area_equals", 3).matches(grid, 0, 2, context))
        self.assertTrue(ScopePredicate("on_border").matches(grid, 0, 1, context))
        self.assertFalse(ScopePredicate("on_border").matches(grid, 1, 1, context))


if __name__ == "__main__":
    unittest.main()
