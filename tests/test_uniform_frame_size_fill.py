from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.hypotheses import Hypothesis, propose_base_hypotheses


Frame = tuple[int, int, int, int, int]


def _frame_canvas(height: int, width: int, background: int, frames: tuple[Frame, ...]) -> list[list[int]]:
    grid = [[background for _ in range(width)] for _ in range(height)]
    for top, left, interior_height, interior_width, frame_color in frames:
        bottom = top + interior_height + 1
        right = left + interior_width + 1
        for row_index in range(top, bottom + 1):
            for column_index in range(left, right + 1):
                if row_index in {top, bottom} or column_index in {left, right}:
                    grid[row_index][column_index] = frame_color
    return grid


def _filled_frames(
    input_grid: list[list[int]],
    frames: tuple[Frame, ...],
    fill_map: dict[tuple[int, int], int],
) -> list[list[int]]:
    output = [row[:] for row in input_grid]
    for top, left, interior_height, interior_width, _ in frames:
        fill_color = fill_map[(interior_height, interior_width)]
        for row_index in range(top + 1, top + interior_height + 1):
            for column_index in range(left + 1, left + interior_width + 1):
                output[row_index][column_index] = fill_color
    return output


class UniformFrameSizeFillTests(unittest.TestCase):
    def test_rederives_frames_backgrounds_and_visible_size_color_map(self) -> None:
        fill_map = {(1, 2): 3, (2, 2): 4}
        first_frames = ((0, 0, 1, 2, 5), (5, 7, 2, 2, 8))
        first_input = _frame_canvas(10, 13, 0, first_frames)
        first_input[9][0] = 7
        first_output = _filled_frames(first_input, first_frames, fill_map)

        second_frames = ((1, 1, 2, 2, 6), (6, 8, 1, 2, 2))
        second_input = _frame_canvas(10, 13, 9, second_frames)
        second_input[0][12] = 1
        second_output = _filled_frames(second_input, second_frames, fill_map)

        test_frames = ((0, 7, 1, 2, 4), (5, 1, 2, 2, 7))
        test_input = _frame_canvas(10, 13, 1, test_frames)
        test_input[9][12] = 8
        test_output = _filled_frames(test_input, test_frames, fill_map)
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
            operator_families=("identity", "uniform_frame_size_fill"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-uniform-frame-size-fill")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertTrue(result.selected_hypothesis.startswith("uniform_frame_size_fill("))
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in test_output))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        candidates = propose_base_hypotheses(
            environment.training_pairs,
            ("uniform_frame_size_fill",),
        )
        self.assertEqual([candidate.kind for candidate in candidates], ["uniform_frame_size_fill"])

    def test_refuses_unknown_sizes_tied_backgrounds_and_filled_frame_slots(self) -> None:
        hypothesis = Hypothesis(
            "uniform_frame_size_fill",
            (("fill_map", "1x1:6;2x2:7"),),
        )
        unknown_size_frames = ((0, 0, 1, 1, 5), (4, 4, 3, 3, 8))
        unknown_size = _frame_canvas(9, 9, 0, unknown_size_frames)
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in unknown_size)))

        contaminated_frames = ((0, 0, 1, 1, 5), (4, 4, 2, 2, 8))
        contaminated = _frame_canvas(8, 8, 0, contaminated_frames)
        contaminated[1][1] = 2
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in contaminated)))

        tied_background = _frame_canvas(8, 8, 0, contaminated_frames)
        zero_locations = [
            (row_index, column_index)
            for row_index, row in enumerate(tied_background)
            for column_index, color in enumerate(row)
            if color == 0 and (row_index, column_index) not in {(1, 1), (5, 5), (5, 6), (6, 5), (6, 6)}
        ]
        for row_index, column_index in zero_locations[:22]:
            tied_background[row_index][column_index] = 1
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in tied_background)))

    def test_refuses_conflicting_visible_size_to_color_evidence(self) -> None:
        frames = ((0, 0, 1, 1, 5), (4, 4, 2, 2, 8))
        first_input = _frame_canvas(8, 8, 0, frames)
        first_output = _filled_frames(first_input, frames, {(1, 1): 6, (2, 2): 7})
        second_input = _frame_canvas(8, 8, 9, frames)
        second_output = _filled_frames(second_input, frames, {(1, 1): 3, (2, 2): 7})
        environment = ARC12InteractiveEnv.from_task_payload(
            {
                "train": [
                    {"input": first_input, "output": first_output},
                    {"input": second_input, "output": second_output},
                ],
                "test": [{"input": first_input, "output": first_output}],
            }
        )

        self.assertEqual(
            propose_base_hypotheses(
                environment.training_pairs,
                ("uniform_frame_size_fill",),
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
