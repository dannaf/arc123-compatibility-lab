from dataclasses import dataclass

from arc123.controller import IterativeHypothesisLearner


def g(rows):
    return tuple(tuple(row) for row in rows)


@dataclass(frozen=True)
class Env:
    training_pairs: tuple
    test_inputs: tuple


TRAIN = (
    (
        g([[0,0,0,8,0,8,0,0,0],[0,0,0,8,8,8,0,0,0],[0,0,0,8,8,0,0,0,0],[0,0,0,0,0,4,0,0,0],[0,0,0,4,4,4,0,0,0],[0,0,0,0,4,0,0,0,0]]),
        g([[0,0,0,8,0,8,8,0,8],[0,0,0,8,8,8,8,8,8],[0,0,0,8,8,0,0,8,8],[0,0,0,0,0,4,0,0,0],[0,0,0,4,4,4,0,0,0],[0,0,0,0,4,0,0,0,0]]),
    ),
    (
        g([[0,0,0,8,0,8,0,0,0],[0,0,0,0,8,8,0,0,0],[0,0,0,0,0,8,0,0,0],[0,0,0,4,0,0,0,0,0],[0,0,0,4,4,4,0,0,0],[0,0,0,0,4,0,0,0,0]]),
        g([[8,0,8,8,0,8,0,0,0],[8,8,0,0,8,8,0,0,0],[8,0,0,0,0,8,0,0,0],[0,0,0,4,0,0,0,0,0],[0,0,0,4,4,4,0,0,0],[0,0,0,0,4,0,0,0,0]]),
    ),
    (
        g([[0,0,0,8,0,0,0,0,0],[0,0,0,0,8,8,0,0,0],[0,0,0,8,0,0,0,0,0],[0,0,0,4,0,0,0,0,0],[0,0,0,4,4,4,0,0,0],[0,0,0,0,4,0,0,0,0]]),
        g([[0,0,8,8,0,0,0,0,0],[8,8,0,0,8,8,0,0,0],[0,0,8,8,0,0,0,0,0],[0,0,0,4,0,0,0,0,0],[0,0,0,4,4,4,0,0,0],[0,0,0,0,4,0,0,0,0]]),
    ),
)

TEST_INPUT = g([[0,0,0,8,0,8,0,0,0],[0,0,0,0,8,8,0,0,0],[0,0,0,8,0,0,0,0,0],[0,0,0,0,0,4,0,0,0],[0,0,0,4,4,4,0,0,0],[0,0,0,0,4,0,0,0,0]])
TEST_OUTPUT = g([[0,0,0,8,0,8,8,0,8],[0,0,0,0,8,8,8,8,0],[0,0,0,8,0,0,0,0,8],[0,0,0,0,0,4,0,0,0],[0,0,0,4,4,4,0,0,0],[0,0,0,0,4,0,0,0,0]])


def test_arc2_760b3cac_live_cross_object_bridge():
    result = IterativeHypothesisLearner().solve(
        Env(TRAIN, (TEST_INPUT,)), episode_id="760b3cac-regression"
    )
    assert result.training_exact
    assert not result.used_fallback
    assert result.predictions == (TEST_OUTPUT,)
    assert result.selected_hypothesis == "controller_orientation_mirror_copy"
