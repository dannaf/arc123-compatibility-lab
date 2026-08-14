from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.hypotheses import Hypothesis, propose_base_hypotheses


TEMPLATE_MASK = (
    (1, 0, 0),
    (1, 1, 0),
    (1, 1, 1),
)
PAYLOAD_MASK = (
    (1, 1, 0),
    (0, 1, 1),
    (1, 0, 1),
)
ALT_PAYLOAD_MASK = (
    (1, 0, 1),
    (1, 1, 1),
    (0, 1, 0),
)
DOWN_ARROW_MASK = (
    (1, 1, 1),
    (0, 1, 0),
    (0, 1, 0),
)
UP_ARROW_MASK = (
    (0, 1, 0),
    (0, 1, 0),
    (1, 1, 1),
)


def _paint_mask(
    grid: list[list[int]],
    top: int,
    left: int,
    mask: tuple[tuple[int, ...], ...],
    color: int,
) -> None:
    for row_offset, row in enumerate(mask):
        for column_offset, occupied in enumerate(row):
            if occupied:
                grid[top + row_offset][left + column_offset] = color


def _panel_stamp_example(
    *,
    background: int,
    separator: int,
    template_color: int,
    arrow_color: int,
    payload_color: int,
    direction: str,
    anchor_top: int,
    anchor_left: int,
    role_tops: tuple[int, int, int],
    payload_mask: tuple[tuple[int, ...], ...] = PAYLOAD_MASK,
) -> tuple[list[list[int]], list[list[int]]]:
    width = 15
    upper_height = 5
    lower_height = 9
    divider_row = upper_height
    input_grid = [
        [background for _ in range(width)]
        for _ in range(upper_height + 1 + lower_height)
    ]
    expected_output = [
        [background for _ in range(width)]
        for _ in range(lower_height)
    ]
    input_grid[divider_row] = [separator for _ in range(width)]
    template_top, arrow_top, payload_top = role_tops
    _paint_mask(input_grid, template_top, 1, TEMPLATE_MASK, template_color)
    _paint_mask(
        input_grid,
        arrow_top,
        6,
        DOWN_ARROW_MASK if direction == "down" else UP_ARROW_MASK,
        arrow_color,
    )
    _paint_mask(input_grid, payload_top, 11, payload_mask, payload_color)
    _paint_mask(
        input_grid,
        divider_row + 1 + anchor_top,
        anchor_left,
        TEMPLATE_MASK,
        template_color,
    )
    _paint_mask(expected_output, anchor_top, anchor_left, TEMPLATE_MASK, template_color)
    destination_top = anchor_top + 3 if direction == "down" else anchor_top - 3
    _paint_mask(expected_output, destination_top, anchor_left, payload_mask, payload_color)
    return input_grid, expected_output


def _copy_grid(grid: list[list[int]]) -> list[list[int]]:
    return [row[:] for row in grid]


class SeparatorArrowGuidedPanelStampTests(unittest.TestCase):
    def test_rederives_dynamic_roles_direction_and_stamp_from_demonstrations(self) -> None:
        first_input, first_output = _panel_stamp_example(
            background=0,
            separator=5,
            template_color=1,
            arrow_color=2,
            payload_color=7,
            direction="down",
            anchor_top=2,
            anchor_left=5,
            role_tops=(1, 1, 1),
        )
        second_input, second_output = _panel_stamp_example(
            background=9,
            separator=6,
            template_color=3,
            arrow_color=1,
            payload_color=8,
            direction="up",
            anchor_top=5,
            anchor_left=4,
            role_tops=(0, 2, 1),
            payload_mask=ALT_PAYLOAD_MASK,
        )
        test_input, test_output = _panel_stamp_example(
            background=4,
            separator=0,
            template_color=6,
            arrow_color=2,
            payload_color=9,
            direction="down",
            anchor_top=1,
            anchor_left=8,
            role_tops=(1, 0, 2),
            payload_mask=ALT_PAYLOAD_MASK,
        )
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
            operator_families=("identity", "separator_arrow_guided_panel_stamp"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-separator-arrow-guided-panel-stamp")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "separator_arrow_guided_panel_stamp")
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in test_output))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        candidates = propose_base_hypotheses(
            environment.training_pairs,
            ("separator_arrow_guided_panel_stamp",),
        )
        self.assertEqual(
            [candidate.kind for candidate in candidates],
            ["separator_arrow_guided_panel_stamp"],
        )

    def test_refuses_ambiguous_roles_mismatched_templates_and_blocked_stamps(self) -> None:
        input_grid, _ = _panel_stamp_example(
            background=0,
            separator=5,
            template_color=1,
            arrow_color=2,
            payload_color=7,
            direction="down",
            anchor_top=2,
            anchor_left=5,
            role_tops=(1, 1, 1),
        )
        hypothesis = Hypothesis("separator_arrow_guided_panel_stamp")

        ambiguous_arrow, _ = _panel_stamp_example(
            background=0,
            separator=5,
            template_color=1,
            arrow_color=2,
            payload_color=7,
            direction="down",
            anchor_top=2,
            anchor_left=5,
            role_tops=(1, 1, 1),
            payload_mask=DOWN_ARROW_MASK,
        )
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in ambiguous_arrow)))

        mismatched_template = _copy_grid(input_grid)
        mismatched_template[8][5] = 0
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in mismatched_template)))

        blocked_destination = _copy_grid(input_grid)
        blocked_destination[11][5] = 1
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in blocked_destination)))

        extra_divider = _copy_grid(input_grid)
        extra_divider[0] = [5 for _ in extra_divider[0]]
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in extra_divider)))

    def test_refuses_conflicting_visible_output_evidence(self) -> None:
        first_input, first_output = _panel_stamp_example(
            background=0,
            separator=5,
            template_color=1,
            arrow_color=2,
            payload_color=7,
            direction="down",
            anchor_top=2,
            anchor_left=5,
            role_tops=(1, 1, 1),
        )
        second_input, second_output = _panel_stamp_example(
            background=9,
            separator=6,
            template_color=3,
            arrow_color=1,
            payload_color=8,
            direction="up",
            anchor_top=5,
            anchor_left=4,
            role_tops=(0, 2, 1),
        )
        conflicting_output = _copy_grid(second_output)
        conflicting_output[0][0] = 8
        environment = ARC12InteractiveEnv.from_task_payload(
            {
                "train": [
                    {"input": first_input, "output": first_output},
                    {"input": second_input, "output": conflicting_output},
                ],
                "test": [{"input": first_input, "output": first_output}],
            }
        )

        self.assertEqual(
            propose_base_hypotheses(
                environment.training_pairs,
                ("separator_arrow_guided_panel_stamp",),
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
