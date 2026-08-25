from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.geometric_relation_hypotheses import propose_geometric_relation_hypotheses


def _shear(grid):
    background = 0
    foreground = [
        (r, c, value)
        for r, row in enumerate(grid)
        for c, value in enumerate(row)
        if value != background
    ]
    bottom = max(r for r, _, _ in foreground)
    out = [[background for _ in row] for row in grid]
    width = len(grid[0])
    for r, c, value in foreground:
        nc = c - (bottom - r)
        if 0 <= nc < width:
            out[r][nc] = value
    return out


def _pair(grid):
    return tuple(map(tuple, grid)), tuple(map(tuple, _shear(grid)))


def test_bottom_anchored_shear_generalizes_across_shape_color_and_clipping():
    g1 = [
        [0, 0, 4, 4, 4, 0, 0],
        [0, 0, 4, 0, 4, 0, 0],
        [0, 0, 4, 4, 4, 0, 0],
    ]
    g2 = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 7, 7, 0, 0],
        [0, 0, 0, 0, 7, 0, 0],
        [0, 0, 0, 7, 7, 0, 0],
    ]
    training = (_pair(g1), _pair(g2))
    candidates = propose_geometric_relation_hypotheses(
        training, ("bottom_anchored_left_shear",)
    )
    assert len(candidates) == 1

    # Top row clips on the left; the lower rows remain in-bounds.  This makes
    # boundary behavior part of the counterfactual rather than an untested detail.
    test = [
        [0, 0, 9, 9, 9, 0],
        [0, 9, 0, 0, 9, 0],
        [0, 9, 9, 9, 9, 0],
        [0, 0, 9, 9, 0, 0],
    ]
    test_input, expected = _pair(test)
    assert candidates[0].predict(test_input) == expected


def test_live_controller_reaches_singularity_on_shear_relation():
    grids = [
        [
            [0, 0, 4, 4, 4, 0, 0],
            [0, 0, 4, 0, 4, 0, 0],
            [0, 0, 4, 4, 4, 0, 0],
        ],
        [
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 7, 7, 0, 0],
            [0, 0, 0, 0, 7, 0, 0],
            [0, 0, 0, 7, 7, 0, 0],
        ],
    ]
    train = [
        {"input": grid, "output": _shear(grid)}
        for grid in grids
    ]
    test = [
        [0, 0, 9, 9, 9, 0],
        [0, 9, 0, 0, 9, 0],
        [0, 9, 9, 9, 9, 0],
        [0, 0, 9, 9, 0, 0],
    ]
    env = ARC12InteractiveEnv.from_task_payload(
        {"train": train, "test": [{"input": test, "output": _shear(test)}]}
    )
    result = IterativeHypothesisLearner(
        operator_families=("identity", "bottom_anchored_left_shear")
    ).solve(env, "shear-counterfactual")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "bottom_anchored_left_shear"
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]
