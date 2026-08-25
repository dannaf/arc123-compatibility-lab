from dataclasses import dataclass

from arc123.controller import IterativeHypothesisLearner


def g(rows):
    return tuple(tuple(row) for row in rows)


@dataclass(frozen=True)
class Env:
    training_pairs: tuple
    test_inputs: tuple


TRAIN = (
    (g([[7,9],[4,3]]), g([[7,9,7,9,7,9],[4,3,4,3,4,3],[9,7,9,7,9,7],[3,4,3,4,3,4],[7,9,7,9,7,9],[4,3,4,3,4,3]])),
    (g([[8,6],[6,4]]), g([[8,6,8,6,8,6],[6,4,6,4,6,4],[6,8,6,8,6,8],[4,6,4,6,4,6],[8,6,8,6,8,6],[6,4,6,4,6,4]])),
)
TEST_INPUT = g([[3,2],[7,8]])
TEST_OUTPUT = g([[3,2,3,2,3,2],[7,8,7,8,7,8],[2,3,2,3,2,3],[8,7,8,7,8,7],[3,2,3,2,3,2],[7,8,7,8,7,8]])


def test_arc2_00576224_live_parity_indicator_tiling():
    result = IterativeHypothesisLearner().solve(Env(TRAIN, (TEST_INPUT,)), episode_id="00576224-regression")
    assert result.training_exact
    assert not result.used_fallback
    assert result.predictions == (TEST_OUTPUT,)
    assert result.selected_hypothesis == "alternating_horizontal_mirror_tile"
