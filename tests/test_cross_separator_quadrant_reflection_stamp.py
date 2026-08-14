from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.hypotheses import Hypothesis, propose_base_hypotheses


def _cross_input(
    panel: tuple[tuple[int, ...], ...],
    active_index: int,
    background: int,
    separator: int,
) -> list[list[int]]:
    height = len(panel)
    width = len(panel[0])
    blank = tuple(tuple(background for _ in range(width)) for _ in range(height))
    quadrants = [blank, blank, blank, blank]
    quadrants[active_index] = panel
    top_left, top_right, bottom_left, bottom_right = quadrants
    return [
        *[
            [*left_row, separator, *right_row]
            for left_row, right_row in zip(top_left, top_right)
        ],
        [separator for _ in range(2 * width + 1)],
        *[
            [*left_row, separator, *right_row]
            for left_row, right_row in zip(bottom_left, bottom_right)
        ],
    ]


class CrossSeparatorQuadrantReflectionStampTests(unittest.TestCase):
    def test_rederives_cross_colors_and_active_quadrant(self) -> None:
        first_input = _cross_input(
            ((1, 0, 0), (1, 1, 0)),
            active_index=0,
            background=0,
            separator=6,
        )
        first_output = [
            [6, 0, 0, 0, 0, 6],
            [6, 6, 0, 0, 6, 6],
            [6, 6, 0, 0, 6, 6],
            [6, 0, 0, 0, 0, 6],
        ]
        second_input = _cross_input(
            ((9, 2, 9), (2, 2, 9)),
            active_index=3,
            background=9,
            separator=4,
        )
        second_output = [
            [9, 4, 4, 4, 4, 9],
            [9, 4, 9, 9, 4, 9],
            [9, 4, 9, 9, 4, 9],
            [9, 4, 4, 4, 4, 9],
        ]
        test_input = _cross_input(
            ((1, 7), (1, 1)),
            active_index=1,
            background=7,
            separator=3,
        )
        test_output = [
            [7, 3, 3, 7],
            [3, 3, 3, 3],
            [3, 3, 3, 3],
            [7, 3, 3, 7],
        ]
        environment = ARC12InteractiveEnv.from_task_payload(
            {
                "train": [
                    {"input": first_input, "output": first_output},
                    {"input": second_input, "output": second_output},
                ],
                "test": [{"input": test_input, "output": test_output}],
            }
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "cross_separator_quadrant_reflection_stamp"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-cross-separator-reflection")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(
            result.selected_hypothesis,
            "cross_separator_quadrant_reflection_stamp",
        )
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in test_output))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        candidates = propose_base_hypotheses(
            environment.training_pairs,
            ("cross_separator_quadrant_reflection_stamp",),
        )
        self.assertEqual(
            [candidate.kind for candidate in candidates],
            ["cross_separator_quadrant_reflection_stamp"],
        )

    def test_refuses_ambiguous_payloads_and_background_separator(self) -> None:
        hypothesis = Hypothesis("cross_separator_quadrant_reflection_stamp")
        ambiguous = _cross_input(
            ((1, 0, 0), (1, 1, 0)),
            active_index=0,
            background=0,
            separator=6,
        )
        ambiguous[3][4] = 1
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in ambiguous)))

        background_separator = _cross_input(
            ((1, 0), (1, 1)),
            active_index=2,
            background=0,
            separator=0,
        )
        self.assertIsNone(
            hypothesis.predict(tuple(tuple(row) for row in background_separator))
        )


if __name__ == "__main__":
    unittest.main()
