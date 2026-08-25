from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.segment_hypotheses import propose_segment_hypotheses


def _blank(h=10, w=14, bg=7):
    return [[bg for _ in range(w)] for _ in range(h)]


def _horizontal_fixture(lengths):
    grid = _blank()
    colors = (2, 4, 9, 1)
    for index, length in enumerate(lengths):
        row = 1 + 2 * index
        for c in range(2, 2 + length):
            grid[row][c] = colors[index]
    target = sorted(lengths, reverse=True)[1]
    out = _blank()
    for index, _ in enumerate(lengths):
        row = 1 + 2 * index
        for c in range(2, 2 + target):
            out[row][c] = colors[index]
    return grid, out


def _vertical_fixture(lengths):
    grid = _blank(12, 14, 0)
    colors = (3, 5, 8, 6)
    for index, length in enumerate(lengths):
        column = 1 + 3 * index
        for r in range(1, 1 + length):
            grid[r][column] = colors[index]
    target = sorted(lengths, reverse=True)[1]
    out = _blank(12, 14, 0)
    for index, _ in enumerate(lengths):
        column = 1 + 3 * index
        for r in range(1, 1 + target):
            out[r][column] = colors[index]
    return grid, out


def _anti_fixture(lengths):
    # Width 20 leaves room for the second-longest target to extend the
    # rightmost synthetic segment without clipping; clipping is tested by the
    # shear grammar separately, not conflated with segment equalization here.
    grid = _blank(12, 20, 0)
    colors = (2, 5, 8, 4)
    anchors = ((9, 1), (10, 5), (9, 10), (10, 14))
    for color, length, (r, c) in zip(colors, lengths, anchors):
        for k in range(length):
            grid[r - k][c + k] = color
    target = sorted(lengths, reverse=True)[1]
    out = _blank(12, 20, 0)
    for color, (r, c) in zip(colors, anchors):
        for k in range(target):
            out[r - k][c + k] = color
    return grid, out


def _pair(pair):
    inp, out = pair
    return tuple(map(tuple, inp)), tuple(map(tuple, out))


def test_second_longest_equalization_transfers_across_orientation_and_palette():
    training = tuple(
        _pair(pair)
        for pair in (
            _horizontal_fixture((2, 7, 11)),
            _vertical_fixture((6, 2, 4, 3)),
        )
    )
    candidates = propose_segment_hypotheses(
        training, ("second_longest_segment_equalize",)
    )
    assert len(candidates) == 1
    test_input, expected = _pair(_anti_fixture((3, 8, 5, 2)))
    assert candidates[0].predict(test_input) == expected


def test_equalization_can_both_extend_and_trim_segments():
    inp, expected = _pair(_horizontal_fixture((1, 5, 10)))
    candidate = propose_segment_hypotheses(
        ((inp, expected),), ("second_longest_segment_equalize",)
    )[0]
    assert candidate.predict(inp) == expected


def test_live_controller_solves_segment_order_statistic_relation():
    train = []
    for pair in (
        _horizontal_fixture((2, 7, 11)),
        _vertical_fixture((6, 2, 4, 3)),
    ):
        inp, out = pair
        train.append({"input": inp, "output": out})
    test_input, expected = _anti_fixture((3, 8, 5, 2))
    env = ARC12InteractiveEnv.from_task_payload(
        {"train": train, "test": [{"input": test_input, "output": expected}]}
    )
    result = IterativeHypothesisLearner(
        operator_families=("identity", "second_longest_segment_equalize")
    ).solve(env, "segment-equalize-counterfactual")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "second_longest_segment_equalize"
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]
