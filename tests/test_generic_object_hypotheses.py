from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.generic_object_hypotheses import (
    propose_component_extract_hypotheses,
    propose_unique_neighbor_propagation_hypotheses,
)


def _grid(rows):
    return tuple(tuple(row) for row in rows)


def test_component_selector_discovers_relational_minimum_not_color_memorization():
    training = (
        (
            _grid([
                [2, 2, 2, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 3],
                [0, 0, 0, 0, 0],
            ]),
            _grid([[3]]),
        ),
        (
            _grid([
                [3, 3, 0, 0, 0],
                [3, 3, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 2, 2],
            ]),
            _grid([[2, 2]]),
        ),
    )
    candidates = propose_component_extract_hypotheses(
        training, ("component_select_extract",)
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.separator.descriptor_names == ("is_min_area",)
    # Swapping colors across demos makes raw color an invalid separator.
    assert candidate.separator.predict({"is_min_area": True}) is True
    assert candidate.separator.predict({"is_min_area": False}) is False


def test_live_controller_uses_component_selector_on_unseen_colors():
    train = [
        {
            "input": [
                [2, 2, 2, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 3],
                [0, 0, 0, 0, 0],
            ],
            "output": [[3]],
        },
        {
            "input": [
                [3, 3, 0, 0, 0],
                [3, 3, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 2, 2],
            ],
            "output": [[2, 2]],
        },
    ]
    test = [
        {
            "input": [
                [4, 4, 4, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 5],
                [0, 0, 0, 0, 0],
            ],
            "output": [[5]],
        }
    ]
    env = ARC12InteractiveEnv.from_task_payload({"train": train, "test": test})
    result = IterativeHypothesisLearner(
        operator_families=("identity", "component_select_extract")
    ).solve(env, "generic-object-extract")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "component_select_extract"
    assert result.predictions[0] == ((5,),)
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]


def test_unique_neighbor_propagation_generalizes_marker_color():
    training = (
        (
            _grid([[0, 2, 8, 8], [0, 0, 0, 0]]),
            _grid([[0, 2, 2, 2], [0, 0, 0, 0]]),
        ),
        (
            _grid([[0, 3, 8, 0], [0, 0, 8, 0], [0, 0, 8, 0]]),
            _grid([[0, 3, 3, 0], [0, 0, 3, 0], [0, 0, 3, 0]]),
        ),
    )
    candidates = propose_unique_neighbor_propagation_hypotheses(
        training, ("unique_neighbor_component_propagation",)
    )
    assert len(candidates) == 1
    assert candidates[0].placeholder_color == 8
    assert candidates[0].predict(_grid([[4, 8, 8, 0], [0, 0, 0, 0]])) == _grid(
        [[4, 4, 4, 0], [0, 0, 0, 0]]
    )


def test_live_controller_uses_neighbor_backdrive_without_task_id():
    train = [
        {
            "input": [[0, 2, 8, 8], [0, 0, 0, 0]],
            "output": [[0, 2, 2, 2], [0, 0, 0, 0]],
        },
        {
            "input": [[0, 3, 8, 0], [0, 0, 8, 0], [0, 0, 8, 0]],
            "output": [[0, 3, 3, 0], [0, 0, 3, 0], [0, 0, 3, 0]],
        },
    ]
    test = [
        {
            "input": [[4, 8, 8, 0], [0, 0, 0, 0]],
            "output": [[4, 4, 4, 0], [0, 0, 0, 0]],
        }
    ]
    env = ARC12InteractiveEnv.from_task_payload({"train": train, "test": test})
    result = IterativeHypothesisLearner(
        operator_families=("identity", "unique_neighbor_component_propagation")
    ).solve(env, "generic-neighbor-backdrive")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "unique_neighbor_component_propagation"
    assert result.predictions[0] == ((4, 4, 4, 0), (0, 0, 0, 0))
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]
