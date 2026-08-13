from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.hypotheses import Hypothesis, propose_base_hypotheses
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

    def test_generic_tile_repeat_infers_integer_output_factors(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[1, 2], [3, 4]],
                    "output": [
                        [1, 2, 1, 2, 1, 2],
                        [3, 4, 3, 4, 3, 4],
                        [1, 2, 1, 2, 1, 2],
                        [3, 4, 3, 4, 3, 4],
                        [1, 2, 1, 2, 1, 2],
                        [3, 4, 3, 4, 3, 4],
                    ],
                },
                {
                    "input": [[5, 6], [7, 8]],
                    "output": [
                        [5, 6, 5, 6, 5, 6],
                        [7, 8, 7, 8, 7, 8],
                        [5, 6, 5, 6, 5, 6],
                        [7, 8, 7, 8, 7, 8],
                        [5, 6, 5, 6, 5, 6],
                        [7, 8, 7, 8, 7, 8],
                    ],
                },
            ],
            [
                {
                    "input": [[9, 0], [0, 9]],
                    "output": [
                        [9, 0, 9, 0, 9, 0],
                        [0, 9, 0, 9, 0, 9],
                        [9, 0, 9, 0, 9, 0],
                        [0, 9, 0, 9, 0, 9],
                        [9, 0, 9, 0, 9, 0],
                        [0, 9, 0, 9, 0, 9],
                    ],
                }
            ],
        )
        result = IterativeHypothesisLearner(
            operator_families=("identity", "repeat_tile")
        ).solve(environment, "synthetic-tile-repeat")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "tile_repeat(column_factor=3,row_factor=3)")
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_rectangular_dihedral_transform_is_inferred_from_visible_examples(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[1, 2, 3], [4, 5, 6]],
                    "output": [[1, 4], [2, 5], [3, 6]],
                },
                {
                    "input": [[7, 8], [9, 0], [1, 2]],
                    "output": [[7, 9, 1], [8, 0, 2]],
                },
            ],
            [
                {
                    "input": [[3, 1, 4, 1], [5, 9, 2, 6]],
                    "output": [[3, 5], [1, 9], [4, 2], [1, 6]],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "dihedral_transform"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-rectangular-transpose")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "dihedral_transform(axis=transpose)")
        self.assertEqual(result.predictions[0], ((3, 5), (1, 9), (4, 2), (1, 6)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_dihedral_tiling_is_inferred_from_visible_macro_blocks(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[7, 9], [4, 3]],
                    "output": [
                        [7, 9, 7, 9, 7, 9],
                        [4, 3, 4, 3, 4, 3],
                        [9, 7, 9, 7, 9, 7],
                        [3, 4, 3, 4, 3, 4],
                        [7, 9, 7, 9, 7, 9],
                        [4, 3, 4, 3, 4, 3],
                    ],
                },
                {
                    "input": [[1, 2], [5, 6]],
                    "output": [
                        [1, 2, 1, 2, 1, 2],
                        [5, 6, 5, 6, 5, 6],
                        [2, 1, 2, 1, 2, 1],
                        [6, 5, 6, 5, 6, 5],
                        [1, 2, 1, 2, 1, 2],
                        [5, 6, 5, 6, 5, 6],
                    ],
                },
            ],
            [
                {
                    "input": [[3, 2], [7, 8]],
                    "output": [
                        [3, 2, 3, 2, 3, 2],
                        [7, 8, 7, 8, 7, 8],
                        [2, 3, 2, 3, 2, 3],
                        [8, 7, 8, 7, 8, 7],
                        [3, 2, 3, 2, 3, 2],
                        [7, 8, 7, 8, 7, 8],
                    ],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "dihedral_tile")
        ).solve(environment, "synthetic-dihedral-tile")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertIn("dihedral_tile", result.selected_hypothesis)
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        actions = [event["action"] for event in result.trace["events"]]
        self.assertLess(actions.index(ActionKind.SPECIALIZE.value), actions.index(ActionKind.COMPOSE_RULE.value))
        self.assertIn(ActionKind.EXPLAIN_RESIDUAL.value, actions)
        compare_snapshots = [
            event["payload"]["current_theory"]
            for event in result.trace["events"]
            if event["action"] == ActionKind.COMPARE.value
            and "current_theory" in event["payload"]
        ]
        self.assertTrue(compare_snapshots)
        self.assertTrue(all("revision_count" in snapshot for snapshot in compare_snapshots))
        self.assertTrue(all("history" not in snapshot for snapshot in compare_snapshots))

    def test_self_mask_macro_stamp_learns_most_frequent_relative_color_role(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[1, 1], [1, 2]],
                    "output": [
                        [1, 1, 1, 1],
                        [1, 2, 1, 2],
                        [1, 1, 0, 0],
                        [1, 2, 0, 0],
                    ],
                },
                {
                    "input": [[3, 4], [3, 3]],
                    "output": [
                        [3, 4, 0, 0],
                        [3, 3, 0, 0],
                        [3, 4, 3, 4],
                        [3, 3, 3, 3],
                    ],
                },
            ],
            [
                {
                    "input": [[7, 7], [8, 7]],
                    "output": [
                        [7, 7, 7, 7],
                        [8, 7, 8, 7],
                        [0, 0, 7, 7],
                        [0, 0, 8, 7],
                    ],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "self_mask_macro_stamp"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-self-mask-most-frequent")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertIn("self_mask_macro_stamp", result.selected_hypothesis)
        self.assertIn("selector=most_frequent", result.selected_hypothesis)
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_self_mask_macro_stamp_learns_zero_mask_and_dynamic_other_color(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[9, 9], [9, 0]],
                    "output": [
                        [0, 0, 0, 0],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0],
                        [0, 0, 0, 9],
                    ],
                },
                {
                    "input": [[0, 0], [5, 0]],
                    "output": [
                        [5, 5, 5, 5],
                        [0, 5, 0, 5],
                        [0, 0, 5, 5],
                        [0, 0, 0, 5],
                    ],
                },
            ],
            [
                {
                    "input": [[1, 0], [0, 1]],
                    "output": [
                        [0, 0, 0, 1],
                        [0, 0, 1, 0],
                        [0, 1, 0, 0],
                        [1, 0, 0, 0],
                    ],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "self_mask_macro_stamp"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-self-mask-zero")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertIn("self_mask_macro_stamp", result.selected_hypothesis)
        self.assertIn("selector=zero", result.selected_hypothesis)
        self.assertIn("template=selected_mask_other_color", result.selected_hypothesis)
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_axis_mode_denoise_rederives_dominant_axis_for_each_grid(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [
                        [1, 1, 1, 2],
                        [1, 1, 2, 1],
                        [1, 1, 1, 2],
                        [2, 2, 3, 2],
                    ],
                    "output": [
                        [1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [2, 2, 2, 2],
                    ],
                },
                {
                    "input": [
                        [1, 1, 1, 2],
                        [1, 1, 1, 2],
                        [1, 2, 1, 3],
                        [2, 1, 2, 2],
                    ],
                    "output": [
                        [1, 1, 1, 2],
                        [1, 1, 1, 2],
                        [1, 1, 1, 2],
                        [1, 1, 1, 2],
                    ],
                },
            ],
            [
                {
                    "input": [
                        [4, 4, 4, 5],
                        [4, 4, 6, 4],
                        [4, 4, 4, 5],
                        [5, 5, 7, 5],
                    ],
                    "output": [
                        [4, 4, 4, 4],
                        [4, 4, 4, 4],
                        [4, 4, 4, 4],
                        [5, 5, 5, 5],
                    ],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "axis_mode_denoise"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-axis-mode-denoise")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "axis_mode_denoise")
        self.assertEqual(
            result.predictions[0],
            ((4, 4, 4, 4), (4, 4, 4, 4), (4, 4, 4, 4), (5, 5, 5, 5)),
        )
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_axis_mode_denoise_refuses_ambiguous_modes_and_axis_ties(self) -> None:
        ambiguous = ((1, 2), (3, 4))
        self.assertIsNone(Hypothesis("axis_mode_denoise").predict(ambiguous))
        self.assertNotIn(
            "axis_mode_denoise",
            {
                candidate.kind
                for candidate in propose_base_hypotheses(
                    ((ambiguous, ambiguous),), ("axis_mode_denoise",)
                )
            },
        )

    def test_self_contained_subset_crop_discovers_input_relative_payload(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [
                        [0, 3, 0, 0, 0, 0, 3],
                        [0, 1, 2, 1, 0, 0, 0],
                        [0, 2, 1, 2, 0, 4, 0],
                        [0, 0, 0, 0, 0, 0, 0],
                        [4, 0, 0, 0, 0, 0, 0],
                    ],
                    "output": [[1, 2, 1], [2, 1, 2]],
                },
                {
                    "input": [
                        [7, 0, 0, 0, 0, 0, 7],
                        [0, 5, 6, 5, 0, 0, 0],
                        [0, 6, 5, 6, 0, 8, 0],
                        [0, 0, 0, 0, 0, 0, 0],
                        [8, 0, 0, 0, 0, 0, 0],
                    ],
                    "output": [[5, 6, 5], [6, 5, 6]],
                },
            ],
            [
                {
                    "input": [
                        [9, 0, 0, 0, 0, 9],
                        [0, 3, 4, 3, 0, 0],
                        [0, 4, 3, 4, 0, 8],
                        [8, 0, 0, 0, 0, 0],
                    ],
                    "output": [[3, 4, 3], [4, 3, 4]],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "self_contained_subset_crop"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-self-contained-subset-crop")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "self_contained_subset_crop")
        self.assertEqual(result.predictions[0], ((3, 4, 3), (4, 3, 4)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_self_contained_subset_crop_refuses_equal_area_payload_ties(self) -> None:
        ambiguous = ((0, 1, 1, 0, 2, 2, 0), (0, 1, 1, 0, 2, 2, 0))
        self.assertIsNone(Hypothesis("self_contained_subset_crop").predict(ambiguous))
        self.assertNotIn(
            "self_contained_subset_crop",
            {
                candidate.kind
                for candidate in propose_base_hypotheses(
                    ((ambiguous, ((1, 1), (1, 1))),),
                    ("self_contained_subset_crop",),
                )
            },
        )

    def test_frame_interior_crop_rederives_a_unique_largest_outline(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [
                        [0, 1, 0, 1, 0, 1],
                        [1, 7, 7, 7, 7, 0],
                        [0, 7, 1, 2, 7, 1],
                        [1, 7, 3, 4, 7, 0],
                        [0, 7, 7, 7, 7, 1],
                    ],
                    "output": [[1, 2], [3, 4]],
                },
                {
                    "input": [
                        [0, 1, 0, 1, 0, 1, 0],
                        [1, 8, 8, 8, 8, 8, 1],
                        [0, 8, 6, 7, 5, 8, 0],
                        [1, 8, 4, 3, 2, 8, 1],
                        [0, 8, 8, 8, 8, 8, 0],
                        [1, 0, 1, 0, 1, 0, 1],
                    ],
                    "output": [[6, 7, 5], [4, 3, 2]],
                },
            ],
            [
                {
                    "input": [
                        [0, 1, 0, 1, 0, 1],
                        [1, 4, 4, 4, 4, 0],
                        [0, 4, 9, 8, 4, 1],
                        [1, 4, 7, 6, 4, 0],
                        [0, 4, 4, 4, 4, 1],
                    ],
                    "output": [[9, 8], [7, 6]],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "frame_interior_crop"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-frame-interior-crop")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "frame_interior_crop")
        self.assertEqual(result.predictions[0], ((9, 8), (7, 6)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_frame_interior_crop_refuses_equal_largest_outline_ties(self) -> None:
        ambiguous = (
            (0, 1, 1, 1, 0, 2, 2, 2, 0),
            (0, 1, 3, 1, 0, 2, 4, 2, 0),
            (0, 1, 1, 1, 0, 2, 2, 2, 0),
        )
        self.assertIsNone(Hypothesis("frame_interior_crop").predict(ambiguous))

    def test_central_separator_cellwise_combine_uses_visible_pairs_only(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[0, 1, 9, 0, 0], [1, 0, 9, 1, 0], [0, 1, 9, 1, 1]],
                    "output": [[0, 2], [1, 0], [2, 1]],
                },
                {
                    "input": [[1, 1, 8, 0, 1], [0, 0, 8, 1, 0], [1, 0, 8, 1, 1]],
                    "output": [[2, 1], [2, 0], [1, 2]],
                },
            ],
            [
                {
                    "input": [[1, 0, 7, 0, 1], [0, 1, 7, 1, 0]],
                    "output": [[2, 2], [2, 2]],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "central_separator_cellwise_combine"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-central-separator-cellwise-combine")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertIn("central_separator_cellwise_combine", result.selected_hypothesis)
        self.assertEqual(result.predictions[0], ((2, 2), (2, 2)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

        candidate = next(
            item
            for item in propose_base_hypotheses(
                environment.training_pairs, ("central_separator_cellwise_combine",)
            )
            if item.kind == "central_separator_cellwise_combine"
        )
        self.assertIsNone(candidate.predict(((2, 0, 7, 0, 0),)))

    def test_adjacent_bilateral_combine_rederives_a_visible_pair_table(self) -> None:
        environment = self._environment(
            [
                {
                    "input": [[0, 3, 0, 2], [3, 0, 2, 0]],
                    "output": [[5, 0], [0, 5]],
                },
                {
                    "input": [[0, 3, 2, 0], [3, 0, 0, 2]],
                    "output": [[0, 0], [0, 0]],
                },
            ],
            [
                {
                    "input": [[0, 3, 0, 0], [0, 3, 2, 2]],
                    "output": [[5, 0], [0, 0]],
                }
            ],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "adjacent_bilateral_cellwise_combine"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-adjacent-bilateral-cellwise-combine")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertIn("adjacent_bilateral_cellwise_combine", result.selected_hypothesis)
        self.assertEqual(result.predictions[0], ((5, 0), (0, 0)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

        candidate = next(
            item
            for item in propose_base_hypotheses(
                environment.training_pairs, ("adjacent_bilateral_cellwise_combine",)
            )
            if item.kind == "adjacent_bilateral_cellwise_combine"
        )
        self.assertIsNone(candidate.predict(((2, 3, 0, 2),)))

    def test_distinct_nonbackground_scale_rederives_its_factor_per_grid(self) -> None:
        def scale_cells(input_grid: list[list[int]], factor: int) -> list[list[int]]:
            expanded_rows = [
                [color for input_color in row for color in [input_color] * factor]
                for row in input_grid
            ]
            return [row for expanded_row in expanded_rows for row in [expanded_row] * factor]

        training_first = [[0, 1], [2, 0]]
        training_second = [[0, 3, 4], [5, 0, 0]]
        test_input = [[0, 6, 7], [8, 9, 0]]
        environment = self._environment(
            [
                {"input": training_first, "output": scale_cells(training_first, 2)},
                {"input": training_second, "output": scale_cells(training_second, 3)},
            ],
            [{"input": test_input, "output": scale_cells(test_input, 4)}],
        )

        result = IterativeHypothesisLearner(
            operator_families=("identity", "distinct_nonbackground_scale"),
            candidate_limit=12,
            beam_width=8,
        ).solve(environment, "synthetic-distinct-nonbackground-scale")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.selected_hypothesis, "distinct_nonbackground_scale")
        self.assertEqual(result.predictions[0], tuple(tuple(row) for row in scale_cells(test_input, 4)))
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])

    def test_distinct_nonbackground_scale_refuses_tied_background_evidence(self) -> None:
        ambiguous = ((1, 2), (3, 4))
        self.assertIsNone(Hypothesis("distinct_nonbackground_scale").predict(ambiguous))
        self.assertNotIn(
            "distinct_nonbackground_scale",
            {
                candidate.kind
                for candidate in propose_base_hypotheses(
                    ((ambiguous, ((1, 1, 2, 2), (1, 1, 2, 2), (3, 3, 4, 4), (3, 3, 4, 4))),),
                    ("distinct_nonbackground_scale",),
                )
            },
        )

    def test_explicit_empty_operator_vocabulary_does_not_restore_defaults(self) -> None:
        environment = self._environment(
            [{"input": [[1]], "output": [[2]]}],
            [{"input": [[1]], "output": [[2]]}],
        )

        result = IterativeHypothesisLearner(operator_families=()).solve(
            environment, "synthetic-empty-vocabulary"
        )

        self.assertFalse(result.training_exact)
        self.assertTrue(result.used_fallback)

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

    def test_svg_uses_a_compact_label_for_identity_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "corpus_callosum.svg"
            render_corpus_callosum_svg(
                path,
                ((1, 2), (3, 4)),
                ((1, 2), (3, 4)),
                "fallback_identity_complete_grid",
                {"events": []},
            )
            rendered = path.read_text(encoding="utf-8")

        self.assertIn("identity fallback", rendered)
        self.assertNotIn("fallback_identity_complete_grid", rendered)


if __name__ == "__main__":
    unittest.main()
