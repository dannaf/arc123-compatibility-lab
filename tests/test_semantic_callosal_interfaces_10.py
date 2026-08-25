from dataclasses import dataclass

from arc123.controller import IterativeHypothesisLearner
from arc123.semantic_hypotheses import (
    EnclosedBackgroundFill,
    RowMarkerColumnMap,
    propose_semantic_hypotheses,
)


def g(rows):
    return tuple(tuple(row) for row in rows)


@dataclass(frozen=True)
class Env:
    training_pairs: tuple
    test_inputs: tuple


A85_TRAIN = (
    (g([[0,0,5],[0,5,0],[5,0,0]]), g([[3,3,3],[4,4,4],[2,2,2]])),
    (g([[0,0,5],[0,0,5],[0,0,5]]), g([[3,3,3],[3,3,3],[3,3,3]])),
    (g([[5,0,0],[0,5,0],[5,0,0]]), g([[2,2,2],[4,4,4],[2,2,2]])),
    (g([[0,5,0],[0,0,5],[0,5,0]]), g([[4,4,4],[3,3,3],[4,4,4]])),
)
A85_TEST_INPUT = g([[0,0,5],[5,0,0],[0,5,0]])
A85_TEST_OUTPUT = g([[3,3,3],[2,2,2],[4,4,4]])

D037_TRAIN = (
    (g([[0,0,6],[0,4,0],[3,0,0]]), g([[0,0,6],[0,4,6],[3,4,6]])),
    (g([[0,2,0],[7,0,8],[0,0,0]]), g([[0,2,0],[7,2,8],[7,2,8]])),
    (g([[4,0,0],[0,2,0],[0,0,0]]), g([[4,0,0],[4,2,0],[4,2,0]])),
)
D037_TEST_INPUT = g([[4,0,8],[0,0,0],[0,7,0]])
D037_TEST_OUTPUT = g([[4,0,8],[4,0,8],[4,7,8]])

ENCLOSURE_INPUT = g([
    [0,0,0,0,0,0],
    [0,0,3,0,0,0],
    [0,3,0,3,0,0],
    [0,0,3,0,3,0],
    [0,0,0,3,0,0],
    [0,0,0,0,0,0],
])
ENCLOSURE_OUTPUT = g([
    [0,0,0,0,0,0],
    [0,0,3,0,0,0],
    [0,3,4,3,0,0],
    [0,0,3,4,3,0],
    [0,0,0,3,0,0],
    [0,0,0,0,0,0],
])


def test_live_learner_repairs_a85d4709_without_task_id():
    result = IterativeHypothesisLearner().solve(
        Env(A85_TRAIN, (A85_TEST_INPUT,)), episode_id="a85d4709-regression"
    )
    assert result.training_exact
    assert not result.used_fallback
    assert result.predictions == (A85_TEST_OUTPUT,)
    assert result.selected_hypothesis == "row_marker_column_to_constant_row"


def test_row_marker_semantic_key_preserves_unknown_when_unseen():
    predictor = RowMarkerColumnMap(((0, 2), (2, 3)))
    prediction = predictor.predict(g([[0,5,0]]))
    assert prediction == ((None, None, None),)


def test_live_learner_repairs_d037b0a7_with_generic_downward_propagation():
    result = IterativeHypothesisLearner().solve(
        Env(D037_TRAIN, (D037_TEST_INPUT,)), episode_id="d037b0a7-regression"
    )
    assert result.training_exact
    assert not result.used_fallback
    assert result.predictions == (D037_TEST_OUTPUT,)
    assert result.selected_hypothesis == "column_downward_propagation"


def test_enclosure_semantic_interface_matches_real_00d62c1b_training_example():
    candidates = propose_semantic_hypotheses(((ENCLOSURE_INPUT, ENCLOSURE_OUTPUT),))
    fills = [candidate for candidate in candidates if isinstance(candidate, EnclosedBackgroundFill)]
    assert len(fills) == 1
    assert fills[0].fill_color == 4
    assert fills[0].predict(ENCLOSURE_INPUT) == ENCLOSURE_OUTPUT
