from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.relational_macro_hypotheses import propose_relational_macro_hypotheses


def _render(grid, line_color):
    h, w = len(grid), len(grid[0])
    seeds = {(r, c): grid[r][c] for r in range(h) for c in range(w) if grid[r][c] != 0}
    diagonals = {r - c for r, c in seeds}
    out = [[0 for _ in range(2 * w)] for _ in range(2 * h)]
    for r in range(h):
        for c in range(w):
            tr, tc = 2 * r, 2 * c
            if (r, c) in seeds:
                value = seeds[(r, c)]
                out[tr][tc] = value
                out[tr][tc + 1] = value
                out[tr + 1][tc] = value
                out[tr + 1][tc + 1] = value
            elif r - c in diagonals:
                out[tr][tc] = line_color
                out[tr + 1][tc + 1] = line_color
    return out


def test_diagonal_closure_is_logical_before_macro_rendering():
    g1 = [[0, 4, 0], [0, 0, 0], [6, 0, 0]]
    g2 = [[3, 0, 0, 0], [0, 0, 5, 0], [0, 0, 0, 0]]
    training = tuple(
        (tuple(map(tuple, grid)), tuple(map(tuple, _render(grid, 8))))
        for grid in (g1, g2)
    )
    candidates = propose_relational_macro_hypotheses(
        training, ("diagonal_closure_macro_render",)
    )
    assert len(candidates) == 1
    assert candidates[0].line_color == 8

    # Two seeds lie on the same logical diagonal; closure is a set operation,
    # not two independently rendered pixel rays.
    test = [[7, 0, 0, 0], [0, 9, 0, 0], [0, 0, 0, 0], [0, 0, 0, 2]]
    assert candidates[0].predict(tuple(map(tuple, test))) == tuple(
        map(tuple, _render(test, 8))
    )


def test_seed_macro_overrides_diagonal_glyph_at_intersection():
    grid = [[0, 0, 5], [0, 4, 0], [0, 0, 0]]
    expected = _render(grid, 1)
    candidate = propose_relational_macro_hypotheses(
        ((tuple(map(tuple, grid)), tuple(map(tuple, expected))),),
        ("diagonal_closure_macro_render",),
    )[0]
    prediction = candidate.predict(tuple(map(tuple, grid)))
    assert prediction == tuple(map(tuple, expected))
    # The seed at logical (1,1) is solid 4 rather than a line-color glyph.
    assert prediction[2][2:4] == (4, 4)
    assert prediction[3][2:4] == (4, 4)


def test_live_controller_solves_diagonal_closure_macro_relation():
    training_grids = (
        [[0, 4, 0], [0, 0, 0], [6, 0, 0]],
        [[3, 0, 0, 0], [0, 0, 5, 0], [0, 0, 0, 0]],
    )
    train = [
        {"input": grid, "output": _render(grid, 8)}
        for grid in training_grids
    ]
    test = [[7, 0, 0, 0], [0, 9, 0, 0], [0, 0, 0, 0], [0, 0, 0, 2]]
    env = ARC12InteractiveEnv.from_task_payload(
        {"train": train, "test": [{"input": test, "output": _render(test, 8)}]}
    )
    result = IterativeHypothesisLearner(
        operator_families=("identity", "diagonal_closure_macro_render")
    ).solve(env, "diagonal-macro-counterfactual")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "diagonal_closure_macro_render"
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]
