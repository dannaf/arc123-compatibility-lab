#!/usr/bin/env python3
"""Exact small ARC1/2 bidirectional corpus-callosum debug packet.

Success cases:
- ARC1 a85d4709: row-marker column <-> output-row color.
- ARC1 0d3d703e: input-color <-> output-color bijection.

Negative-control interface:
- ARC1 evaluation f3e62deb: the observed color->motion interface contains only
  8->right and 6->up in training while held-out objects use colors 4 and 3.
  We exhibit two distinct extensions of that interface which agree on all
  observed color-motion pairs but disagree on the unseen colors. This proves
  that *that semantic interface alone* has no prediction singularity. It is
  not a proof that the whole ARC task is information-theoretically impossible;
  another generic semantic relation could still identify the test behavior.

All arithmetic/comparisons are exact. Test targets for the success cases are
used only in the final post-commit assertions.
"""

from collections import defaultdict
import json

A85 = {
    "train": [
        {"input": [[0,0,5],[0,5,0],[5,0,0]], "output": [[3,3,3],[4,4,4],[2,2,2]]},
        {"input": [[0,0,5],[0,0,5],[0,0,5]], "output": [[3,3,3],[3,3,3],[3,3,3]]},
        {"input": [[5,0,0],[0,5,0],[5,0,0]], "output": [[2,2,2],[4,4,4],[2,2,2]]},
        {"input": [[0,5,0],[0,0,5],[0,5,0]], "output": [[4,4,4],[3,3,3],[4,4,4]]},
    ],
    "test": [{"input": [[0,0,5],[5,0,0],[0,5,0]], "output": [[3,3,3],[2,2,2],[4,4,4]]}],
}

D03 = {
    "train": [
        {"input": [[3,1,2],[3,1,2],[3,1,2]], "output": [[4,5,6],[4,5,6],[4,5,6]]},
        {"input": [[2,3,8],[2,3,8],[2,3,8]], "output": [[6,4,9],[6,4,9],[6,4,9]]},
        {"input": [[5,8,6],[5,8,6],[5,8,6]], "output": [[1,9,2],[1,9,2],[1,9,2]]},
        {"input": [[9,4,2],[9,4,2],[9,4,2]], "output": [[8,3,6],[8,3,6],[8,3,6]]},
    ],
    "test": [{"input": [[8,1,3],[8,1,3],[8,1,3]], "output": [[9,5,4],[9,5,4],[9,5,4]]}],
}


def learn_function(pairs):
    support = defaultdict(set)
    for x, y in pairs:
        support[x].add(y)
    if any(len(v) != 1 for v in support.values()):
        return None, support
    return {x: next(iter(v)) for x, v in support.items()}, support


def a85_result():
    pairs = []
    reverse_pairs = []
    for ex in A85["train"]:
        for inrow, outrow in zip(ex["input"], ex["output"]):
            nz = [i for i, v in enumerate(inrow) if v != 0]
            assert len(nz) == 1
            assert len(set(outrow)) == 1
            pairs.append((nz[0], outrow[0]))
            reverse_pairs.append((outrow[0], nz[0]))
    forward, _ = learn_function(pairs)
    backward, _ = learn_function(reverse_pairs)
    assert forward == {0: 2, 1: 4, 2: 3}
    assert backward == {2: 0, 4: 1, 3: 2}

    def predict(grid):
        out = []
        for row in grid:
            nz = [i for i, v in enumerate(row) if v != 0]
            if len(nz) != 1 or nz[0] not in forward:
                return None
            out.append([forward[nz[0]]] * len(row))
        return out

    committed = predict(A85["test"][0]["input"])
    return {
        "task": "a85d4709",
        "interface": "marker_column <-> constant_output_row_color",
        "forward": forward,
        "backward": backward,
        "training_bidirectional_deterministic": True,
        "committed_prediction": committed,
        "test_exact_post_commit": committed == A85["test"][0]["output"],
    }


def d03_result():
    pairs = []
    for ex in D03["train"]:
        for xr, yr in zip(ex["input"], ex["output"]):
            pairs.extend(zip(xr, yr))
    forward, _ = learn_function(pairs)
    reverse, _ = learn_function([(y, x) for x, y in pairs])
    assert forward is not None and reverse is not None
    assert len(forward) == len(reverse) == 8
    committed = [[forward[v] for v in row] for row in D03["test"][0]["input"]]
    return {
        "task": "0d3d703e",
        "interface": "input_color <-> output_color",
        "forward": forward,
        "backward": reverse,
        "bijective_on_observed_support": True,
        "committed_prediction": committed,
        "test_exact_post_commit": committed == D03["test"][0]["output"],
    }


def f3_interface_result():
    observed = {8: "right", 6: "up"}
    # Both hypotheses are exact extensions of the observed interface.
    h1 = {8: "right", 6: "up", 4: "down", 3: "left"}
    h2 = {8: "right", 6: "up", 4: "left", 3: "down"}
    assert all(h1[k] == v and h2[k] == v for k, v in observed.items())
    assert h1[4] != h2[4] and h1[3] != h2[3]
    return {
        "task": "f3e62deb",
        "interface": "object_color -> boundary_motion_direction",
        "observed_training_support": observed,
        "heldout_colors": [4, 3],
        "two_training-compatible_extensions": [h1, h2],
        "prediction_singularity_at_this_interface": False,
        "correct_status_before_extra_semantics": "UNKNOWN",
        "claim_boundary": "This refutes only the color->direction interface as sufficient; it does not refute every possible generic semantic rule for the task.",
    }


def main():
    result = {
        "a85d4709": a85_result(),
        "0d3d703e": d03_result(),
        "f3e62deb_interface_negative_control": f3_interface_result(),
    }
    assert result["a85d4709"]["test_exact_post_commit"]
    assert result["0d3d703e"]["test_exact_post_commit"]
    assert not result["f3e62deb_interface_negative_control"]["prediction_singularity_at_this_interface"]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
