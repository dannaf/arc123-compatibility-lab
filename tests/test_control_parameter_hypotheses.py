from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.control_parameter_hypotheses import propose_control_parameter_hypotheses
from arc123.controller import IterativeHypothesisLearner


def _corner_frame_pair(marker_a, marker_b):
    """8x8 grid with a 6x6 frame and two adjacent external corner markers."""

    corner_cell = {
        "tl": (0, 0),
        "tr": (0, 7),
        "bl": (7, 0),
        "br": (7, 7),
    }
    corner_code = {
        "tl": (0, 0),
        "tr": (0, 1),
        "bl": (1, 0),
        "br": (1, 1),
    }
    grid = [[0 for _ in range(8)] for _ in range(8)]
    for row in range(1, 7):
        for column in range(1, 7):
            if row in {1, 6} or column in {1, 6}:
                grid[row][column] = 5
    for corner, color in (marker_a, marker_b):
        row, column = corner_cell[corner]
        grid[row][column] = color

    output = [row[:] for row in grid]
    for corner, color in (marker_a, marker_b):
        vr, hc = corner_code[corner]
        targets = {(vr, hc), (1 - vr, 1 - hc)}
        for row in range(2, 6):
            qrow = 0 if row <= 3 else 1
            for column in range(2, 6):
                qcol = 0 if column <= 3 else 1
                if (qrow, qcol) in targets:
                    output[row][column] = color
    return grid, output


def _palette_cycle_pair(height: int, run_length: int, palette: tuple[int, ...]):
    width = len(palette) + 4
    palette_start = width - len(palette)
    target_column = palette_start - 1
    grid = [[0 for _ in range(width)] for _ in range(height)]
    for row in range(run_length):
        grid[row][0] = 5
    for offset, color in enumerate(palette):
        for row in range(height):
            grid[row][palette_start + offset] = color

    output = [row[:] for row in grid]
    for row in range(height):
        for column in range(palette_start, width):
            output[row][column] = 0
        output[row][target_column] = palette[(row // run_length) % len(palette)]
    return grid, output


def _as_pair(pair):
    inp, out = pair
    return tuple(map(tuple, inp)), tuple(map(tuple, out))


def test_corner_marker_rule_survives_marker_position_and_color_counterfactuals():
    training = tuple(
        _as_pair(pair)
        for pair in (
            _corner_frame_pair(("tl", 4), ("tr", 8)),
            _corner_frame_pair(("tr", 6), ("br", 7)),
        )
    )
    candidates = propose_control_parameter_hypotheses(
        training, ("corner_marker_diagonal_quadrant_fill",)
    )
    assert len(candidates) == 1
    test_input, expected = _as_pair(_corner_frame_pair(("bl", 9), ("br", 1)))
    assert candidates[0].predict(test_input) == expected


def test_live_controller_solves_corner_marker_relation_without_task_dispatch():
    train = []
    for pair in (
        _corner_frame_pair(("tl", 4), ("tr", 8)),
        _corner_frame_pair(("tr", 6), ("br", 7)),
    ):
        inp, out = pair
        train.append({"input": inp, "output": out})
    test_input, expected = _corner_frame_pair(("bl", 9), ("br", 1))
    env = ARC12InteractiveEnv.from_task_payload(
        {"train": train, "test": [{"input": test_input, "output": expected}]}
    )
    result = IterativeHypothesisLearner(
        operator_families=("identity", "corner_marker_diagonal_quadrant_fill")
    ).solve(env, "corner-marker-counterfactual")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "corner_marker_diagonal_quadrant_fill"
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]


def test_marker_count_is_a_parameter_not_a_memorized_sequence():
    training = tuple(
        _as_pair(pair)
        for pair in (
            _palette_cycle_pair(9, 2, (4, 8, 3)),
            _palette_cycle_pair(8, 1, (2, 6)),
        )
    )
    candidates = propose_control_parameter_hypotheses(
        training, ("marker_count_palette_cycle",)
    )
    assert len(candidates) == 1
    test_input, expected = _as_pair(_palette_cycle_pair(11, 3, (7, 1, 9)))
    assert candidates[0].predict(test_input) == expected


def test_live_controller_solves_count_controlled_palette_cycle():
    train = []
    for pair in (
        _palette_cycle_pair(9, 2, (4, 8, 3)),
        _palette_cycle_pair(8, 1, (2, 6)),
    ):
        inp, out = pair
        train.append({"input": inp, "output": out})
    test_input, expected = _palette_cycle_pair(11, 3, (7, 1, 9))
    env = ARC12InteractiveEnv.from_task_payload(
        {"train": train, "test": [{"input": test_input, "output": expected}]}
    )
    result = IterativeHypothesisLearner(
        operator_families=("identity", "marker_count_palette_cycle")
    ).solve(env, "count-palette-counterfactual")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "marker_count_palette_cycle"
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]
