from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.hypotheses import Hypothesis, propose_base_hypotheses


def _scale_cells(input_grid: list[list[int]], factor: int) -> list[list[int]]:
    expanded_rows = [
        [color for input_color in row for color in [input_color] * factor]
        for row in input_grid
    ]
    return [row for expanded_row in expanded_rows for row in [expanded_row] * factor]


def _quadrants(
    top_left: list[list[int]],
    top_right: list[list[int]],
    bottom_left: list[list[int]],
    bottom_right: list[list[int]],
    separator: int,
) -> list[list[int]]:
    width = len(top_left[0])
    rows = [
        left_row + [separator] + right_row
        for left_row, right_row in zip(top_left, top_right)
    ]
    rows.append([separator] * (width * 2 + 1))
    rows.extend(
        left_row + [separator] + right_row
        for left_row, right_row in zip(bottom_left, bottom_right)
    )
    return rows


def _border(height: int, width: int, background: int, foreground: int) -> list[list[int]]:
    return [
        [
            foreground if row in {0, height - 1} or column in {0, width - 1} else background
            for column in range(width)
        ]
        for row in range(height)
    ]


def _line(size: int, background: int, foreground: int, motif: str) -> list[list[int]]:
    cells = {
        "top_row": {(0, column) for column in range(size)},
        "main_diagonal": {(index, index) for index in range(size)},
        "anti_diagonal": {(index, size - 1 - index) for index in range(size)},
    }[motif]
    return [
        [foreground if (row, column) in cells else background for column in range(size)]
        for row in range(size)
    ]


class P0028GenericPortfolioTests(unittest.TestCase):
    def _environment(self, train: list[dict], test: list[dict]) -> ARC12InteractiveEnv:
        return ARC12InteractiveEnv.from_task_payload({"train": train, "test": test})

    def test_translation_candidates_are_visible_evidence_exact_before_beam_pruning(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[0, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                    "output": [[0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                },
                {
                    "input": [[0, 0, 0, 0], [2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                    "output": [[0, 0, 0, 0], [0, 0, 0, 0], [0, 2, 2, 0], [0, 0, 0, 0]],
                },
            ],
            [
                {
                    "input": [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 3, 0], [0, 0, 0, 0]],
                    "output": [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 3]],
                }
            ],
        )

        candidates = propose_base_hypotheses(environment.training_pairs, ("translate",))
        self.assertEqual(
            [candidate.name for candidate in candidates],
            ["translate(column_offset=1,row_offset=1)"],
        )
        result = IterativeHypothesisLearner(
            operator_families=("identity", "translate"), candidate_limit=2, beam_width=1
        ).solve(environment, "synthetic-exact-translation")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "translate(column_offset=1,row_offset=1)")
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        ambiguous = ((0, 0), (0, 0))
        self.assertNotIn(
            "translate",
            {
                candidate.kind
                for candidate in propose_base_hypotheses(
                    ((ambiguous, ambiguous),), ("translate",)
                )
            },
        )

    def test_distinct_color_scale_rederives_total_palette_factor(self) -> None:
        first = [[1, 1], [2, 1]]
        second = [[3, 4], [5, 4]]
        uniform = [[7, 7], [7, 7]]
        test_input = [[6, 7], [8, 9]]
        environment = self._environment(
            [
                {"input": first, "output": _scale_cells(first, 2)},
                {"input": second, "output": _scale_cells(second, 3)},
                {"input": uniform, "output": _scale_cells(uniform, 1)},
            ],
            [{"input": test_input, "output": _scale_cells(test_input, 4)}],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "distinct_color_scale"), candidate_limit=4, beam_width=2
        ).solve(environment, "synthetic-distinct-color-scale")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "distinct_color_scale")
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in _scale_cells(test_input, 4)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_quadrant_odd_one_out_requires_a_unique_central_cross_outlier(self) -> None:
        same_first = [[1, 0], [0, 1]]
        odd_first = [[1, 1], [0, 1]]
        same_second = [[2, 0], [2, 2]]
        odd_second = [[0, 2], [2, 2]]
        same_test = [[3, 3], [0, 3]]
        odd_test = [[3, 0], [3, 3]]
        environment = self._environment(
            [
                {
                    "input": _quadrants(
                        same_first, same_first, same_first, odd_first, separator=9
                    ),
                    "output": odd_first,
                },
                {
                    "input": _quadrants(
                        same_second, odd_second, same_second, same_second, separator=8
                    ),
                    "output": odd_second,
                },
            ],
            [
                {
                    "input": _quadrants(same_test, same_test, odd_test, same_test, separator=7),
                    "output": odd_test,
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "quadrant_odd_one_out"), candidate_limit=4, beam_width=2
        ).solve(environment, "synthetic-quadrant-odd-one-out")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "quadrant_odd_one_out")
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in odd_test))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        self.assertIsNone(
            Hypothesis("quadrant_odd_one_out").predict(
                tuple(tuple(row) for row in _quadrants(same_first, same_first, same_first, same_first, 9))
            )
        )

    def test_singleton_foreground_border_rederives_canvas_and_seed_color(self) -> None:
        first = [[0, 0, 0, 0, 0], [0, 4, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
        second = [[6, 6, 6], [6, 6, 6], [6, 2, 6], [6, 6, 6], [6, 6, 6]]
        test_input = [[5, 5, 5, 5], [5, 5, 5, 5], [5, 5, 9, 5], [5, 5, 5, 5], [5, 5, 5, 5], [5, 5, 5, 5]]
        environment = self._environment(
            [
                {"input": first, "output": _border(4, 5, 0, 4)},
                {"input": second, "output": _border(5, 3, 6, 2)},
            ],
            [{"input": test_input, "output": _border(6, 4, 5, 9)}],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "singleton_foreground_border"), candidate_limit=4, beam_width=2
        ).solve(environment, "synthetic-singleton-foreground-border")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "singleton_foreground_border")
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in _border(6, 4, 5, 9)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        self.assertIsNone(Hypothesis("singleton_foreground_border").predict(((1, 0, 0), (0, 0, 0), (0, 0, 0))))
        self.assertIsNone(Hypothesis("singleton_foreground_border").predict(((0, 0, 0), (0, 2, 3), (0, 0, 0))))

    def test_distinct_color_count_line_learns_only_observed_count_motifs(self) -> None:
        one_color = [[2, 2, 2], [2, 2, 2], [2, 2, 2]]
        two_colors = [[2, 2, 2], [2, 3, 2], [2, 2, 2]]
        three_colors = [[2, 3, 4], [2, 2, 2], [2, 2, 2]]
        test_input = [[3, 4, 2], [2, 3, 4], [4, 2, 3]]
        environment = self._environment(
            [
                {"input": one_color, "output": _line(3, 0, 8, "top_row")},
                {"input": two_colors, "output": _line(3, 0, 8, "main_diagonal")},
                {"input": three_colors, "output": _line(3, 0, 8, "anti_diagonal")},
            ],
            [{"input": test_input, "output": _line(3, 0, 8, "anti_diagonal")}],
        )

        candidates = propose_base_hypotheses(environment.training_pairs, ("distinct_color_count_line",))
        self.assertEqual(len(candidates), 1)
        result = IterativeHypothesisLearner(
            operator_families=("identity", "distinct_color_count_line"), candidate_limit=4, beam_width=2
        ).solve(environment, "synthetic-distinct-color-count-line")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertIn("distinct_color_count_line", result.selected_hypothesis)
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in _line(3, 0, 8, "anti_diagonal")))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        self.assertIsNone(candidates[0].predict(((1, 2, 3), (4, 1, 2), (3, 4, 1))))
        conflicting = (
            (tuple(tuple(row) for row in two_colors), tuple(tuple(row) for row in _line(3, 0, 8, "top_row"))),
            (tuple(tuple(row) for row in two_colors), tuple(tuple(row) for row in _line(3, 0, 8, "main_diagonal"))),
        )
        self.assertEqual(propose_base_hypotheses(conflicting, ("distinct_color_count_line",)), [])


if __name__ == "__main__":
    unittest.main()
