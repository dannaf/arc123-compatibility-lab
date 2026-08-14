from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.hypotheses import Hypothesis, propose_base_hypotheses


REPEATED_MASK = (
    (1, 0, 0),
    (0, 1, 1),
    (1, 0, 0),
)
ODD_MASK = (
    (1, 0, 1),
    (1, 1, 1),
    (1, 0, 1),
)


def _colored_panel(mask: tuple[tuple[int, ...], ...], background: int, color: int) -> list[list[int]]:
    return [
        [color if occupied else background for occupied in row]
        for row in mask
    ]


def _horizontal_panels(panels: list[list[list[int]]]) -> list[list[int]]:
    return [
        [color for panel in panels for color in panel[row_index]]
        for row_index in range(len(panels[0]))
    ]


def _vertical_panels(panels: list[list[list[int]]]) -> list[list[int]]:
    return [row for panel in panels for row in panel]


class RepeatedPanelOddOneOutCropTests(unittest.TestCase):
    def test_rederives_orientation_and_shared_background_per_grid(self) -> None:
        first_output = _colored_panel(ODD_MASK, 0, 6)
        second_output = _colored_panel(ODD_MASK, 9, 8)
        test_output = _colored_panel(ODD_MASK, 4, 5)
        environment = ARC12InteractiveEnv.from_task_payload(
            {
                "train": [
                    {
                        "input": _horizontal_panels(
                            [
                                _colored_panel(REPEATED_MASK, 0, 1),
                                _colored_panel(REPEATED_MASK, 0, 2),
                                first_output,
                                _colored_panel(REPEATED_MASK, 0, 7),
                            ]
                        ),
                        "output": first_output,
                    },
                    {
                        "input": _vertical_panels(
                            [
                                _colored_panel(REPEATED_MASK, 9, 1),
                                second_output,
                                _colored_panel(REPEATED_MASK, 9, 2),
                            ]
                        ),
                        "output": second_output,
                    },
                ],
                "test": [
                    {
                        "input": _vertical_panels(
                            [
                                _colored_panel(REPEATED_MASK, 4, 1),
                                _colored_panel(REPEATED_MASK, 4, 2),
                                test_output,
                                _colored_panel(REPEATED_MASK, 4, 7),
                                _colored_panel(REPEATED_MASK, 4, 8),
                            ]
                        ),
                        "output": test_output,
                    }
                ],
            }
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "repeated_panel_odd_one_out_crop"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-repeated-panel-odd-one-out")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(
            result.selected_hypothesis,
            "repeated_panel_odd_one_out_crop(output_height=3,output_width=3)",
        )
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in test_output))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

        candidates = propose_base_hypotheses(
            environment.training_pairs,
            ("repeated_panel_odd_one_out_crop",),
        )
        self.assertEqual([candidate.kind for candidate in candidates], ["repeated_panel_odd_one_out_crop"])

    def test_refuses_tied_masks_and_nonunique_shared_background(self) -> None:
        hypothesis = Hypothesis(
            "repeated_panel_odd_one_out_crop",
            (("output_height", 3), ("output_width", 3)),
        )
        tied_masks = _horizontal_panels(
            [
                _colored_panel(REPEATED_MASK, 0, 1),
                _colored_panel(ODD_MASK, 0, 2),
                _colored_panel(REPEATED_MASK, 0, 3),
                _colored_panel(ODD_MASK, 0, 4),
            ]
        )
        shared_colors = _horizontal_panels(
            [
                [[0, 9, 0], [9, 0, 9], [0, 9, 0]],
                [[0, 9, 0], [9, 9, 9], [0, 9, 0]],
                [[0, 9, 0], [0, 9, 0], [0, 9, 0]],
            ]
        )

        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in tied_masks)))
        self.assertIsNone(hypothesis.predict(tuple(tuple(row) for row in shared_colors)))


if __name__ == "__main__":
    unittest.main()
