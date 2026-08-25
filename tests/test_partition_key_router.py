from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.partition_hypotheses import propose_partition_hypotheses


def _task_grid(key_macro, a, b):
    # 2x2 macro grid of 2x2 compartments with divider color 5.  Zero remains
    # the modal non-divider value. Three ordinary blocks contain three
    # nonbackground cells; the key block is uniquely sparse with two.
    blocks = {
        (0, 0): [[1, 2], [3, 0]],
        (0, 1): [[2, 3], [4, 0]],
        (1, 0): [[3, 4], [1, 0]],
        (1, 1): [[4, 1], [2, 0]],
    }
    blocks[key_macro] = [[0, a], [b, 0]]
    rows = []
    for mr in range(2):
        for lr in range(2):
            rows.append(blocks[(mr, 0)][lr] + [5] + blocks[(mr, 1)][lr])
        if mr == 0:
            rows.append([5, 5, 5, 5, 5])
    return rows


def _target(a, b):
    return [
        [0, 0, 5, a, a],
        [0, 0, 5, a, a],
        [5, 5, 5, 5, 5],
        [b, b, 5, 0, 0],
        [b, b, 5, 0, 0],
    ]


def _pair(key_macro, a, b):
    return (
        tuple(map(tuple, _task_grid(key_macro, a, b))),
        tuple(map(tuple, _target(a, b))),
    )


def test_partition_key_router_is_relational_not_key_position_or_color_specific():
    training = (
        _pair((0, 1), 7, 8),
        _pair((1, 1), 9, 6),
    )
    candidates = propose_partition_hypotheses(
        training, ("partition_key_block_routing",)
    )
    assert len(candidates) == 2
    for candidate in candidates:
        assert all(candidate.predict(inp) == out for inp, out in training)
        assert candidate.predict(tuple(map(tuple, _task_grid((0, 0), 4, 6)))) == tuple(
            map(tuple, _target(4, 6))
        )


def test_live_controller_reaches_prediction_singularity_across_equivalent_key_selectors():
    train = [
        {"input": _task_grid((0, 1), 7, 8), "output": _target(7, 8)},
        {"input": _task_grid((1, 1), 9, 6), "output": _target(9, 6)},
    ]
    test = [
        {"input": _task_grid((0, 0), 4, 6), "output": _target(4, 6)}
    ]
    env = ARC12InteractiveEnv.from_task_payload({"train": train, "test": test})
    result = IterativeHypothesisLearner(
        operator_families=("identity", "partition_key_block_routing")
    ).solve(env, "partition-key-routing")
    assert result.training_exact
    assert not result.used_fallback
    assert result.predictions[0] == tuple(map(tuple, _target(4, 6)))
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]
