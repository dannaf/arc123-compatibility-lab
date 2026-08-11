from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.model import ActionKind, SupportState
from arc123.traces import render_corpus_callosum_svg


class IterativeHypothesisLearnerTests(unittest.TestCase):
    def _environment(self, train: list[dict], test: list[dict]) -> ARC12InteractiveEnv:
        return ARC12InteractiveEnv.from_task_payload({"train": train, "test": test})

    def test_recolor_is_discovered_from_demonstrations_without_test_target_access(self) -> None:
        environment = self._environment(
            [
                {"input": [[0, 1], [1, 0]], "output": [[0, 2], [2, 0]]},
                {"input": [[1, 0], [0, 1]], "output": [[2, 0], [0, 2]]},
            ],
            [{"input": [[1, 1], [0, 1]], "output": [[2, 2], [0, 2]]}],
        )
        result = IterativeHypothesisLearner().solve(environment, "synthetic-recolor")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.predictions[0], ((2, 2), (0, 2)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        actions = [event["action"] for event in result.trace["events"]]
        self.assertIn(ActionKind.ATTEND.value, actions)
        self.assertIn(ActionKind.PROPOSE.value, actions)
        self.assertIn(ActionKind.COMPARE.value, actions)
        self.assertIn(ActionKind.COMMIT.value, actions)

    def test_counterexample_directed_specialization_discovers_generic_line_extension(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[0, 1, 0], [0, 0, 0], [0, 0, 0]],
                    "output": [[0, 1, 0], [0, 1, 0], [0, 1, 0]],
                },
                {
                    "input": [[0, 0, 1], [0, 0, 0], [0, 0, 0]],
                    "output": [[0, 0, 1], [0, 0, 1], [0, 0, 1]],
                },
            ],
            [
                {
                    "input": [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
                    "output": [[1, 0, 0], [1, 0, 0], [1, 0, 0]],
                }
            ],
        )
        result = IterativeHypothesisLearner().solve(environment, "synthetic-line")

        self.assertTrue(result.training_exact)
        self.assertEqual(result.predictions[0], ((1, 0, 0), (1, 0, 0), (1, 0, 0)))
        actions = [event["action"] for event in result.trace["events"]]
        self.assertIn(ActionKind.FIND_COUNTEREXAMPLE.value, actions)
        self.assertIn(ActionKind.SPECIALIZE.value, actions)
        self.assertIn(ActionKind.PROMOTE_CONSTRAINT.value, actions)

    def test_unknown_partial_prediction_is_not_an_impossible_zero(self) -> None:
        environment = self._environment(
            [{"input": [[0, 1], [0, 0]], "output": [[0, 2], [0, 0]]}],
            [{"input": [[0, 1], [0, 0]], "output": [[0, 2], [0, 0]]}],
        )
        feedback = environment.compatibility_feedback(
            0, ((None, 2), (None, None))
        )

        self.assertEqual(feedback.support_state, SupportState.UNKNOWN)
        self.assertFalse(feedback.exact_support_zero)
        self.assertEqual(feedback.unknown_cell_count, 3)
        self.assertEqual(feedback.contradiction_count, 0)

    def test_agent_view_excludes_test_target_and_svg_is_renderable(self) -> None:
        environment = self._environment(
            [{"input": [[0, 1]], "output": [[0, 2]]}],
            [{"input": [[1, 0]], "output": [[2, 0]]}],
        )
        view = environment.agent_view()
        self.assertEqual(view["test_inputs"], [[[1, 0]]])
        self.assertFalse(view["test_targets_visible"])
        self.assertNotIn("expected_output", view)

        result = IterativeHypothesisLearner().solve(environment, "synthetic-svg")
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "corpus_callosum.svg"
            render_corpus_callosum_svg(
                path,
                environment.test_inputs[0],
                result.predictions[0],
                result.selected_hypothesis,
                result.trace,
            )
            rendered = path.read_text(encoding="utf-8")
        self.assertIn("<svg", rendered)
        self.assertIn("Compatibility core", rendered)
        self.assertIn("UNKNOWN", rendered)


if __name__ == "__main__":
    unittest.main()
