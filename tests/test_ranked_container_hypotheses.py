from __future__ import annotations

from arc123.adapters.arc12 import ARC12InteractiveEnv
from arc123.controller import IterativeHypothesisLearner
from arc123.ranked_container_hypotheses import propose_ranked_container_hypotheses


def _grid(endpoint: int, interior: int, rank: int, lengths=(5, 3, 1)):
    height = 9
    width = 9
    rows = [[0 for _ in range(width)] for _ in range(height)]
    for column in range(rank):
        rows[0][column] = endpoint
    bottom = 8
    for column, length in zip((3, 5, 7), lengths):
        top = bottom - length - 1
        rows[top][column] = endpoint
        for row in range(top + 1, bottom):
            rows[row][column] = interior
        rows[bottom][column] = endpoint
    return rows


def _target(endpoint: int, interior: int, rank: int, lengths=(5, 3, 1)):
    rows = _grid(endpoint, interior, rank, lengths)
    bottom = 8
    selected_column = (3, 5, 7)[rank - 1]
    selected_length = lengths[rank - 1]
    top = bottom - selected_length - 1
    for row in range(top + 1, bottom):
        rows[row][selected_column] = endpoint
    return rows


def _pair(endpoint: int, interior: int, rank: int):
    return (
        tuple(map(tuple, _grid(endpoint, interior, rank))),
        tuple(map(tuple, _target(endpoint, interior, rank))),
    )


def test_ranked_container_rule_generalizes_colors_and_rank():
    training = (_pair(2, 5, 2), _pair(3, 7, 1))
    candidates = propose_ranked_container_hypotheses(
        training, ("legend_count_ranked_container_fill",)
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    test_input = tuple(map(tuple, _grid(4, 6, 3)))
    expected = tuple(map(tuple, _target(4, 6, 3)))
    assert candidate.predict(test_input) == expected


def test_live_controller_reaches_ranked_container_prediction_singularity():
    train = [
        {"input": _grid(2, 5, 2), "output": _target(2, 5, 2)},
        {"input": _grid(3, 7, 1), "output": _target(3, 7, 1)},
    ]
    test = [{"input": _grid(4, 6, 3), "output": _target(4, 6, 3)}]
    env = ARC12InteractiveEnv.from_task_payload({"train": train, "test": test})
    result = IterativeHypothesisLearner(
        operator_families=("identity", "legend_count_ranked_container_fill")
    ).solve(env, "ranked-container")
    assert result.training_exact
    assert not result.used_fallback
    assert result.selected_hypothesis == "legend_count_ranked_container_fill"
    assert env.post_answer_validate(result.predictions)[0]["all_cells_match"]


def test_invalid_unseen_rank_stays_unknown():
    training = (_pair(2, 5, 1),)
    # Constant one-demonstration relation is still exactly replayable by this
    # typed transform; the guardrail is at prediction time.
    candidates = propose_ranked_container_hypotheses(
        training, ("legend_count_ranked_container_fill",)
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    invalid = _grid(4, 6, 3, lengths=(5, 3))
    assert candidate.predict(tuple(map(tuple, invalid))) is None
