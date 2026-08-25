from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.measurement_hypotheses import propose_measurement_hypotheses


def _expected(grid):
    # Fixtures deliberately use background 0; expected height is one plus the
    # number of 4-connected foreground components.
    seen = set()
    count = 0
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            if value == 0 or (r, c) in seen:
                continue
            count += 1
            stack = [(r, c)]
            seen.add((r, c))
            while stack:
                x, y = stack.pop()
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if (
                        0 <= nx < len(grid)
                        and 0 <= ny < len(grid[0])
                        and grid[nx][ny] != 0
                        and (nx, ny) not in seen
                    ):
                        seen.add((nx, ny))
                        stack.append((nx, ny))
    return [[0] for _ in range(count + 1)]


def _pair(grid):
    return tuple(map(tuple, grid)), tuple(map(tuple, _expected(grid)))


def test_component_count_controls_output_dimension_not_component_shape_or_color():
    one = [
        [0, 4, 4, 0],
        [0, 0, 4, 0],
        [0, 0, 0, 0],
    ]
    three = [
        [7, 0, 0, 0, 6],
        [7, 0, 9, 0, 0],
        [0, 0, 9, 0, 0],
    ]
    training = (_pair(one), _pair(three))
    candidates = propose_measurement_hypotheses(
        training, ("component_count_plus_one_blank_column",)
    )
    assert len(candidates) == 1

    four = [
        [3, 0, 5, 0, 0],
        [0, 0, 0, 0, 8],
        [6, 6, 0, 0, 8],
    ]
    test_input, expected = _pair(four)
    assert candidates[0].predict(test_input) == expected


def test_diagonal_touching_does_not_merge_four_connected_components():
    grid = [
        [2, 0, 0],
        [0, 2, 0],
        [0, 0, 2],
    ]
    candidate = propose_measurement_hypotheses(
        (_pair(grid),), ("component_count_plus_one_blank_column",)
    )[0]
    assert candidate.predict(tuple(map(tuple, grid))) == tuple((0,) for _ in range(4))


def test_live_controller_solves_measurement_to_dimension_relation():
    training_grids = [
        [[0, 4, 4, 0], [0, 0, 4, 0], [0, 0, 0, 0]],
        [[7, 0, 0, 0, 6], [7, 0, 9, 0, 0], [0, 0, 9, 0, 0]],
    ]
    train = [{"input": grid, "output": _expected(grid)} for grid in training_grids]
    test = [[3, 0, 5, 0, 0], [0, 0, 0, 0, 8], [6, 6, 0, 0, 8]]
    env = ARC12InteractiveEnv.from_task_payload(
        {"train": train, "test": [{"input": test, "output": _expected(test)}]}
    )
    result = IterativeHypothesisLearner(
        operator_families=("identity", "component_count_plus_one_blank_column")
    ).solve(env, "component-count-counterfactual")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "component_count_plus_one_blank_column"
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]
