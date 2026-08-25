from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.generic_object_hypotheses import (
    propose_component_extract_hypotheses,
    propose_unique_neighbor_propagation_hypotheses,
)


def _grid(rows):
    return tuple(tuple(row) for row in rows)


def _two_component_training():
    return (
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


def test_component_selector_preserves_min_vs_not_max_ambiguity():
    candidates = propose_component_extract_hypotheses(
        _two_component_training(), ("component_select_extract",)
    )
    fields = {candidate.separator.descriptor_names for candidate in candidates}
    # With exactly two objects per demonstration, these two explanations are
    # observationally equivalent.  The learner must not erase that ambiguity.
    assert ("is_min_area",) in fields
    assert ("is_max_area",) in fields


def test_ambiguous_exact_semantic_models_block_prediction_singularity():
    train = [
        {"input": [list(row) for row in inp], "output": [list(row) for row in out]}
        for inp, out in _two_component_training()
    ]
    test = [
        {
            "input": [
                [4, 4, 4, 0, 0, 0],
                [0, 0, 0, 0, 5, 5],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 6],
            ],
            "output": [[6]],
        }
    ]
    env = ARC12InteractiveEnv.from_task_payload({"train": train, "test": test})
    result = IterativeHypothesisLearner(
        operator_families=("identity", "component_select_extract")
    ).solve(env, "ambiguous-object-extract")
    # is_min_area predicts the singleton 6.  "not is_max_area" selects both
    # non-max objects and cannot make one crop. Both remain training-exact, so
    # strict prediction singularity correctly refuses to commit.
    assert not result.training_exact
    assert result.used_fallback
    assert any(
        event.get("reason") == "prediction_singularity_blocked_by_unknown_exact_models"
        for event in result.trace["events"]
    )


def test_extra_training_world_disambiguates_minimum_and_generalizes_unseen_colors():
    train = [
        {"input": [list(row) for row in inp], "output": [list(row) for row in out]}
        for inp, out in _two_component_training()
    ]
    train.append(
        {
            "input": [
                [2, 2, 0, 0, 0, 0],
                [2, 2, 0, 0, 3, 3],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 4],
            ],
            "output": [[4]],
        }
    )
    test = [
        {
            "input": [
                [5, 5, 5, 0, 0, 0],
                [0, 0, 0, 0, 6, 6],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 7],
            ],
            "output": [[7]],
        }
    ]
    env = ARC12InteractiveEnv.from_task_payload({"train": train, "test": test})
    result = IterativeHypothesisLearner(
        operator_families=("identity", "component_select_extract")
    ).solve(env, "disambiguated-object-extract")
    assert result.training_exact
    assert not result.used_fallback
    assert result.predictions[0] == ((7,),)
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
