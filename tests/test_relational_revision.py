from __future__ import annotations

import unittest

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.relational import (
    infer_component_property_erase_specs,
    infer_component_property_recolor_specs,
)
from arc123.theory import PartialTheory, TheoryRule, evaluate_theory_demo


def _grid(height: int, width: int, background: int, cells: dict[tuple[int, int], int]) -> list[list[int]]:
    result = [[background for _ in range(width)] for _ in range(height)]
    for (row, column), color in cells.items():
        result[row][column] = color
    return result


class RelationalRevisionTests(unittest.TestCase):
    def test_marker_shape_mapping_and_marker_erasure_are_composed(self) -> None:
        plus_marker = {(4, 3): 1, (5, 2): 1, (5, 3): 1, (5, 4): 1, (6, 3): 1}
        line_marker = {(4, 2): 1, (4, 3): 1, (4, 4): 1}
        target = {(1, 1): 8, (1, 2): 8, (2, 1): 8, (2, 2): 8}
        plus_input = _grid(8, 8, 0, {**target, **plus_marker})
        line_input = _grid(8, 8, 0, {**target, **line_marker})
        plus_output = _grid(8, 8, 0, {(1, 1): 2, (1, 2): 2, (2, 1): 2, (2, 2): 2})
        line_output = _grid(8, 8, 0, {(1, 1): 3, (1, 2): 3, (2, 1): 3, (2, 2): 3})
        environment = ARC12InteractiveEnv.from_task_payload(
            {
                "train": [
                    {"input": plus_input, "output": plus_output},
                    {"input": line_input, "output": line_output},
                ],
                "test": [{"input": plus_input, "output": plus_output}],
            }
        )

        result = IterativeHypothesisLearner(
            candidate_limit=12,
            beam_width=8,
            max_revisions=96,
            operator_families=("identity", "marker_shape_target_recolor"),
        ).solve(environment, "synthetic-marker-relation")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        self.assertIn("marker_shape_target_recolor", result.selected_hypothesis)
        self.assertIn("erase(color=1,to=input_background)", result.selected_hypothesis)
        actions = [event["action"] for event in result.trace["events"]]
        self.assertIn("FIND_COUNTEREXAMPLE", actions)
        self.assertIn("CHOOSE_NEXT_DEMO", actions)
        self.assertIn("COMPOSE_RULE", actions)

    def test_symmetry_recolor_and_singleton_erase_are_separate_partial_rules(self) -> None:
        horizontal_one = {(0, 0): 2, (0, 1): 2, (0, 2): 2, (1, 1): 2}
        horizontal_two = {
            (0, 0): 2,
            (0, 1): 2,
            (0, 2): 2,
            (0, 3): 2,
            (0, 4): 2,
            (1, 2): 2,
        }
        vertical_one = {(0, 6): 2, (1, 5): 2, (1, 6): 2, (2, 6): 2}
        vertical_two = {(0, 7): 2, (1, 7): 2, (2, 6): 2, (2, 7): 2, (3, 7): 2, (4, 7): 2}
        asymmetric_one = {(4, 0): 2, (5, 0): 2, (5, 1): 2}
        asymmetric_two = {(4, 2): 2, (4, 3): 2, (5, 3): 2, (6, 3): 2}
        singleton_one = {(7, 8): 2}
        singleton_two = {(7, 9): 2}

        first_input = _grid(
            9,
            12,
            0,
            {**horizontal_one, **vertical_one, **asymmetric_one, **singleton_one},
        )
        first_output = _grid(
            9,
            12,
            0,
            {
                **{cell: 3 for cell in horizontal_one},
                **{cell: 4 for cell in vertical_one},
                **{cell: 5 for cell in asymmetric_one},
            },
        )
        second_input = _grid(
            9,
            12,
            7,
            {**horizontal_two, **vertical_two, **asymmetric_two, **singleton_two},
        )
        second_output = _grid(
            9,
            12,
            7,
            {
                **{cell: 3 for cell in horizontal_two},
                **{cell: 4 for cell in vertical_two},
                **{cell: 5 for cell in asymmetric_two},
            },
        )
        test_input = _grid(
            9,
            12,
            6,
            {**horizontal_two, **vertical_one, **asymmetric_two, **singleton_one},
        )
        test_output = _grid(
            9,
            12,
            6,
            {
                **{cell: 3 for cell in horizontal_two},
                **{cell: 4 for cell in vertical_one},
                **{cell: 5 for cell in asymmetric_two},
            },
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
        recolor_spec = next(
            item
            for item in infer_component_property_recolor_specs(environment.training_pairs)
            if item.property_name == "symmetry"
        )
        erase_spec = next(
            item
            for item in infer_component_property_erase_specs(environment.training_pairs)
            if item.property_name == "shape"
        )
        theory = PartialTheory(
            "T0001",
            None,
            (
                TheoryRule.identity(),
                TheoryRule.component_property_recolor(
                    "recolor-by-symmetry", recolor_spec.property_name, recolor_spec.mapping
                ),
                TheoryRule.component_property_erase(
                    "erase-singletons", erase_spec.property_name, erase_spec.values
                ),
            ),
        )

        for demo_index, (input_grid, output_grid) in enumerate(environment.training_pairs):
            support = evaluate_theory_demo(theory, demo_index, input_grid, output_grid).support
            self.assertEqual(support.contradiction_count, 0)
            self.assertEqual(support.unknown_cell_count, 0)
        prediction = tuple(
            tuple(int(color) for color in row) for row in theory.predict(environment.test_inputs[0])
        )
        self.assertTrue(environment.post_answer_validate((prediction,))[0]["all_cells_match"])

    def test_counterexample_revises_row_span_selection_to_global_minimum(self) -> None:
        first_input = _grid(
            4,
            8,
            0,
            {(0, 0): 1, (0, 2): 1, (2, 1): 1, (2, 6): 1},
        )
        first_output = _grid(
            4,
            8,
            0,
            {(0, 0): 1, (0, 1): 1, (0, 2): 1, (2, 1): 1, (2, 6): 1},
        )
        second_input = _grid(
            4,
            8,
            0,
            {(1, 1): 1, (1, 4): 1, (3, 0): 1, (3, 2): 1},
        )
        second_output = _grid(
            4,
            8,
            0,
            {(1, 1): 1, (1, 4): 1, (3, 0): 1, (3, 1): 1, (3, 2): 1},
        )
        test_input = _grid(
            4,
            8,
            0,
            {(0, 2): 1, (0, 4): 1, (2, 0): 1, (2, 5): 1},
        )
        test_output = _grid(
            4,
            8,
            0,
            {(0, 2): 1, (0, 3): 1, (0, 4): 1, (2, 0): 1, (2, 5): 1},
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
            candidate_limit=12,
            beam_width=8,
            max_revisions=128,
            operator_families=("identity", "row_span_fill", "row_span_minimum"),
        ).solve(environment, "synthetic-minimum-span")

        self.assertTrue(result.training_exact)
        self.assertFalse(result.used_fallback)
        self.assertTrue(environment.post_answer_validate(result.predictions)[0]["all_cells_match"])
        self.assertIn("selection=global_minimum", result.selected_hypothesis)
        self.assertTrue(
            any(
                event["action"] == "BIND_PARAMETER"
                and event["payload"].get("parameter") == "selection"
                and event["payload"].get("value") == "global_minimum"
                for event in result.trace["events"]
            )
        )


if __name__ == "__main__":
    unittest.main()
