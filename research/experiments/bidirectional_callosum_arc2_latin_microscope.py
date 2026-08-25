#!/usr/bin/env python3
"""Exact bidirectional/local compatibility microscope on ARC-AGI-2 4cd1b7b2.

The task is learned from TRAIN evidence as a 4x4 completion whose visible clues are
preserved and whose completed rows and columns are permutations of 1..4.
For each missing cell, row and column candidate sets are the two local directional
views. Their exact intersection is the callosal singularity at that cell.

The held-out test output is used only after the train-derived schema commits a
complete prediction.
"""

import json

DIGITS = {1, 2, 3, 4}

TASK = {
    "train": [
        {"input": [[0,4,2,3],[4,1,0,2],[0,3,4,0],[3,0,1,4]], "output": [[1,4,2,3],[4,1,3,2],[2,3,4,1],[3,2,1,4]]},
        {"input": [[1,0,3,4],[0,0,2,1],[2,1,4,0],[0,3,1,2]], "output": [[1,2,3,4],[3,4,2,1],[2,1,4,3],[4,3,1,2]]},
        {"input": [[3,0,2,1],[1,0,0,0],[4,3,0,2],[0,1,4,3]], "output": [[3,4,2,1],[1,2,3,4],[4,3,1,2],[2,1,4,3]]},
    ],
    "test": [
        {"input": [[0,1,2,3],[0,3,1,0],[3,0,4,1],[0,4,0,2]], "output": [[4,1,2,3],[2,3,1,4],[3,2,4,1],[1,4,3,2]]}
    ],
}


def preserves_clues(inp, out):
    return all(inp[r][c] == 0 or inp[r][c] == out[r][c] for r in range(4) for c in range(4))


def rows_are_permutations(out):
    return all(set(row) == DIGITS for row in out)


def columns_are_permutations(out):
    return all({out[r][c] for r in range(4)} == DIGITS for c in range(4))


def learn_schema_from_train():
    properties = {
        "preserve_clues": all(preserves_clues(ex["input"], ex["output"]) for ex in TASK["train"]),
        "row_permutation_1_4": all(rows_are_permutations(ex["output"]) for ex in TASK["train"]),
        "column_permutation_1_4": all(columns_are_permutations(ex["output"]) for ex in TASK["train"]),
    }
    assert all(properties.values())
    return properties


def row_candidates(grid, r, c):
    assert grid[r][c] == 0
    return DIGITS - {v for v in grid[r] if v != 0}


def column_candidates(grid, r, c):
    assert grid[r][c] == 0
    return DIGITS - {grid[i][c] for i in range(4) if grid[i][c] != 0}


def solve_by_bidirectional_intersection(inp):
    grid = [row[:] for row in inp]
    trace = []
    while True:
        changed = False
        for r in range(4):
            for c in range(4):
                if grid[r][c] != 0:
                    continue
                forward = row_candidates(grid, r, c)
                backward = column_candidates(grid, r, c)
                fiber = forward & backward
                trace.append({
                    "cell": [r, c],
                    "row_forward_support": sorted(forward),
                    "column_backward_support": sorted(backward),
                    "shared_callosal_fiber": sorted(fiber),
                    "singular": len(fiber) == 1,
                })
                if not fiber:
                    raise AssertionError(f"empty compatibility fiber at {(r,c)}")
                if len(fiber) == 1:
                    grid[r][c] = next(iter(fiber))
                    changed = True
        if not changed:
            break
    return grid, trace


def run():
    schema = learn_schema_from_train()
    train_checks = []
    for ex in TASK["train"]:
        pred, trace = solve_by_bidirectional_intersection(ex["input"])
        train_checks.append({
            "exact": pred == ex["output"],
            "collapse_count": sum(step["singular"] for step in trace),
            "remaining_unknown": sum(v == 0 for row in pred for v in row),
        })
        assert pred == ex["output"]

    test_pred, test_trace = solve_by_bidirectional_intersection(TASK["test"][0]["input"])
    assert all(v != 0 for row in test_pred for v in row)
    # Only now perform post-commit V&V against the held-out output.
    test_exact = test_pred == TASK["test"][0]["output"]
    assert test_exact

    return {
        "task": "4cd1b7b2",
        "benchmark": "ARC-AGI-2",
        "learned_train_schema": schema,
        "train_checks": train_checks,
        "test_prediction": test_pred,
        "test_exact_post_commit": test_exact,
        "test_trace": test_trace,
        "test_singular_collapses": sum(step["singular"] for step in test_trace),
        "test_remaining_unknown": sum(v == 0 for row in test_pred for v in row),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
