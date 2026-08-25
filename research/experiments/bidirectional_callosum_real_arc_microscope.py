#!/usr/bin/env python3
"""Exact real-task microscope for bidirectional corpus-callosum learning.

Tasks:
- ARC-AGI-1 training task 007bbfb7
- d037b0a7, used in the repo's ARC2-labelled rediscovery packet

Learning uses training input/output only. Test outputs below are post-commit V&V fixtures.
Pure stdlib; all comparisons are exact integer/grid equalities.
"""

from collections import Counter, defaultdict
from fractions import Fraction
import json

TASK_007 = {
    "train": [
        {"input": [[0,7,7],[7,7,7],[0,7,7]], "output": [[0,0,0,0,7,7,0,7,7],[0,0,0,7,7,7,7,7,7],[0,0,0,0,7,7,0,7,7],[0,7,7,0,7,7,0,7,7],[7,7,7,7,7,7,7,7,7],[0,7,7,0,7,7,0,7,7],[0,0,0,0,7,7,0,7,7],[0,0,0,7,7,7,7,7,7],[0,0,0,0,7,7,0,7,7]]},
        {"input": [[4,0,4],[0,0,0],[0,4,0]], "output": [[4,0,4,0,0,0,4,0,4],[0,0,0,0,0,0,0,0,0],[0,4,0,0,0,0,0,4,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,4,0,4,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,4,0,0,0,0]]},
        {"input": [[0,0,0],[0,0,2],[2,0,2]], "output": [[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,2],[0,0,0,0,0,0,2,0,2],[0,0,0,0,0,0,0,0,0],[0,0,2,0,0,0,0,0,2],[2,0,2,0,0,0,2,0,2]]},
        {"input": [[6,6,0],[6,0,0],[0,6,6]], "output": [[6,6,0,6,6,0,0,0,0],[6,0,0,6,0,0,0,0,0],[0,6,6,0,6,6,0,0,0],[6,6,0,0,0,0,0,0,0],[6,0,0,0,0,0,0,0,0],[0,6,6,0,0,0,0,0,0],[0,0,0,6,6,0,6,6,0],[0,0,0,6,0,0,6,0,0],[0,0,0,0,6,6,0,6,6]]},
        {"input": [[2,2,2],[0,0,0],[0,2,2]], "output": [[2,2,2,2,2,2,2,2,2],[0,0,0,0,0,0,0,0,0],[0,2,2,0,2,2,0,2,2],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0],[0,0,0,2,2,2,2,2,2],[0,0,0,0,0,0,0,0,0],[0,0,0,0,2,2,0,2,2]]},
    ],
    "test": [{"input": [[7,0,7],[7,0,7],[7,7,0]], "output": [[7,0,7,0,0,0,7,0,7],[7,0,7,0,0,0,7,0,7],[7,7,0,0,0,0,7,7,0],[7,0,7,0,0,0,7,0,7],[7,0,7,0,0,0,7,0,7],[7,7,0,0,0,0,7,7,0],[7,0,7,7,0,7,0,0,0],[7,0,7,7,0,7,0,0,0],[7,7,0,7,7,0,0,0,0]]}],
}

TASK_D037 = {
    "train": [
        {"input": [[0,0,6],[0,4,0],[3,0,0]], "output": [[0,0,6],[0,4,6],[3,4,6]]},
        {"input": [[0,2,0],[7,0,8],[0,0,0]], "output": [[0,2,0],[7,2,8],[7,2,8]]},
        {"input": [[4,0,0],[0,2,0],[0,0,0]], "output": [[4,0,0],[4,2,0],[4,2,0]]},
    ],
    "test": [{"input": [[4,0,8],[0,0,0],[0,7,0]], "output": [[4,0,8],[4,0,8],[4,7,8]]}],
}


def stamp_micro_if_macro_nonzero(x):
    h, w = len(x), len(x[0])
    return [[x[r % h][c % w] if x[r // h][c // w] != 0 else 0
             for c in range(w * w)] for r in range(h * h)]


def stamp_macro_if_micro_nonzero(x):
    h, w = len(x), len(x[0])
    return [[x[r // h][c // w] if x[r % h][c % w] != 0 else 0
             for c in range(w * w)] for r in range(h * h)]


def tile(x):
    h, w = len(x), len(x[0])
    return [[x[r % h][c % w] for c in range(w * w)] for r in range(h * h)]


def scale_macro(x):
    h, w = len(x), len(x[0])
    return [[x[r // h][c // w] for c in range(w * w)] for r in range(h * h)]


def identity(x):
    return [row[:] for row in x]


def fill_down(x):
    h, w = len(x), len(x[0])
    out = [[0] * w for _ in range(h)]
    for c in range(w):
        active = 0
        for r in range(h):
            if x[r][c] != 0:
                active = x[r][c]
            out[r][c] = active
    return out


def fill_up(x):
    h, w = len(x), len(x[0])
    out = [[0] * w for _ in range(h)]
    for c in range(w):
        active = 0
        for r in range(h - 1, -1, -1):
            if x[r][c] != 0:
                active = x[r][c]
            out[r][c] = active
    return out


def fill_both(x):
    h, w = len(x), len(x[0])
    out = [row[:] for row in x]
    for c in range(w):
        vals = [x[r][c] for r in range(h) if x[r][c] != 0]
        if len(vals) == 1:
            for r in range(h):
                out[r][c] = vals[0]
    return out


def collapse_vertical_runs_to_sources(y):
    h, w = len(y), len(y[0])
    x = [[0] * w for _ in range(h)]
    for c in range(w):
        prev = 0
        for r in range(h):
            v = y[r][c]
            if v != 0 and prev == 0:
                x[r][c] = v
            prev = v
    return x


def exact_on_train(task, fn):
    return all(fn(ex["input"]) == ex["output"] for ex in task["train"])


def run_007():
    candidates = {
        "tile": tile,
        "scale_macro": scale_macro,
        "micro_if_macro_nonzero": stamp_micro_if_macro_nonzero,
        "macro_if_micro_nonzero": stamp_macro_if_micro_nonzero,
    }
    survivors = [name for name, fn in candidates.items() if exact_on_train(TASK_007, fn)]

    joint = Counter()
    for ex in TASK_007["train"]:
        x, y = ex["input"], ex["output"]
        for r in range(9):
            for c in range(9):
                u = (x[r // 3][c // 3], x[r % 3][c % 3])
                joint[(u, y[r][c])] += 1

    forward_support = defaultdict(set)
    backward_support = defaultdict(set)
    for (u, v), n in joint.items():
        assert n > 0
        forward_support[u].add(v)
        backward_support[v].add(u)

    backward = {}
    for v, us in sorted(backward_support.items()):
        denom = sum(joint[(u, v)] for u in us)
        backward[str(v)] = {
            str(u): str(Fraction(joint[(u, v)], denom)) for u in sorted(us)
        }

    test_groups = defaultdict(list)
    for name in survivors:
        pred = candidates[name](TASK_007["test"][0]["input"])
        test_groups[json.dumps(pred)].append(name)

    committed = candidates[survivors[0]](TASK_007["test"][0]["input"])
    return {
        "task": "007bbfb7",
        "training_survivors": survivors,
        "program_singularity": len(survivors) == 1,
        "prediction_group_count": len(test_groups),
        "prediction_singularity": len(test_groups) == 1,
        "test_exact_post_commit": committed == TASK_007["test"][0]["output"],
        "callosal_joint_support_cells": len(joint),
        "callosal_u_contexts": len(forward_support),
        "forward_deterministic": all(len(vs) == 1 for vs in forward_support.values()),
        "backward_support_cardinality": {str(v): len(us) for v, us in sorted(backward_support.items())},
        "backward_conditionals": backward,
    }


def run_d037():
    candidates = {
        "identity": identity,
        "fill_up": fill_up,
        "fill_down": fill_down,
        "fill_both": fill_both,
    }
    survivor_scores = {
        name: sum(fn(ex["input"]) == ex["output"] for ex in TASK_D037["train"])
        for name, fn in candidates.items()
    }
    survivors = [name for name, score in survivor_scores.items() if score == len(TASK_D037["train"])]
    assert survivors == ["fill_down"]
    committed = fill_down(TASK_D037["test"][0]["input"])
    reverse_train = all(
        collapse_vertical_runs_to_sources(ex["output"]) == ex["input"]
        for ex in TASK_D037["train"]
    )
    return {
        "task": "d037b0a7",
        "candidate_training_exact_counts": survivor_scores,
        "training_survivors": survivors,
        "program_singularity": len(survivors) == 1,
        "backward_training_reconstruction_exact": reverse_train,
        "test_exact_post_commit": committed == TASK_D037["test"][0]["output"],
        "test_reverse_reconstruction_post_vv": collapse_vertical_runs_to_sources(TASK_D037["test"][0]["output"]) == TASK_D037["test"][0]["input"],
    }


def main():
    result = {"007bbfb7": run_007(), "d037b0a7": run_d037()}
    assert result["007bbfb7"]["forward_deterministic"]
    assert result["007bbfb7"]["prediction_singularity"]
    assert result["007bbfb7"]["test_exact_post_commit"]
    assert result["007bbfb7"]["backward_support_cardinality"]["0"] == 9
    assert result["d037b0a7"]["program_singularity"]
    assert result["d037b0a7"]["backward_training_reconstruction_exact"]
    assert result["d037b0a7"]["test_exact_post_commit"]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
