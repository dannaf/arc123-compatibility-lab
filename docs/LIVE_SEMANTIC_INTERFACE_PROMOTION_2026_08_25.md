# Live semantic-interface promotion — 2026-08-25

Related: #6–#10, `dannaf/SingularityML#3659`

## Owner prompt — verbatim

> Continue more

## Executive result

The bidirectional corpus-callosum program has now moved from separate microscopes into the normal `IterativeHypothesisLearner`.

Before this change, the live controller searched:

```text
global generic relations
  -> line/span structural relations
  -> partial composition
  -> fallback
```

It had no generic stage for proposing a new semantic separator when raw/local relations were compatible only at the wrong representation or simply failed to express the task.

The live controller now searches:

```text
global generic relations
  -> line/span structural relations
  -> semantic callosal interfaces
  -> partial composition
  -> prediction-group collapse / fallback
```

The semantic stage is task-ID agnostic and is fed only visible training input/output pairs. Each semantic hypothesis is still evaluated by the same exact compatibility machinery. Unsupported semantic keys remain `UNKNOWN`; observed contradictions receive exact-zero rejection.

## Implemented semantic-interface families

`src/arc123/semantic_hypotheses.py` currently provides:

1. **Row marker column -> constant row effect**
   - compresses a whole input row to the position of its unique non-background marker;
   - learns a crossing table from marker-column to output-row color;
   - unseen marker columns return `UNKNOWN` rather than guessing.

2. **Column downward propagation**
   - semantic state is the currently active source marker in a column;
   - forward view propagates the active value;
   - reverse interpretation backdrives an observed run toward its most recent source marker.

3. **Topological enclosed-background fill**
   - separates border-reachable background from enclosed background by exact 4-neighbor reachability;
   - output fill color backdrives the topological classification.

4. **Rectangular enclosure interior-area -> fill color**
   - identifies hollow rectangular frame components;
   - semantic key is interior area;
   - fills only background interior cells and preserves embedded non-background markers;
   - unseen areas remain `UNKNOWN` inside the frame.

5. **Macro/micro crossing gate**
   - uses the two coordinate readings `(macro_cell, micro_cell)` for self-Kronecker-style 3x3 -> 9x9 tasks;
   - the semantic background value is learned by exact training compatibility rather than assumed to be the modal color;
   - supports the two observationally equivalent 007 directions.

6. **Modal macro stamp**
   - recomputes the modal input color in each evidence world;
   - stamps a complete micro-copy of the input into exactly those macro positions whose source cell has that modal value;
   - blank-block color is learned from training.

7. **Row/column permutation completion**
   - learns the output symbol set;
   - at each blank cell intersects the row-missing and column-missing fibers;
   - commits only singleton intersections and immediately backdrives them;
   - unresolved cells remain `UNKNOWN`.

Semantic hypotheses expose `callosal_summary` metadata and the live trace now records that metadata when applying/promoting a semantic candidate.

## Real-task regressions and transfers

### `a85d4709` — prior P0001 failure repaired

Historical result: fallback identity, all 9 test cells wrong.

Semantic interface learned from demonstrations:

```text
marker column 0 <-> constant output-row color 2
marker column 1 <-> constant output-row color 4
marker column 2 <-> constant output-row color 3
```

The generic `RowMarkerColumnMap` predicts the held-out grid exactly. A dedicated regression requires the live learner to select `row_marker_column_to_constant_row` without receiving task ID or test target.

### `d037b0a7` — prior P0001 failure repaired

Generic `ColumnDownwardPropagation` is exact on all training examples and the held-out test. The live regression requires selection of `column_downward_propagation`.

### `007bbfb7` — microscope promoted into live learner

The semantic proposer finds the macro/micro crossing from training dimensions and exact compatibility. A real implementation bug was caught during this promotion: generic `background_color()` is modal-color based, but one 007 demonstration has foreground color 7 as its majority while the semantic blank is still 0. The macro/micro proposer was therefore corrected to infer the gating/background value by exact training compatibility.

Both macro/micro directional descriptions can survive while inducing the same held-out prediction; this is prediction singularity without program singularity.

### ARC2 `4cd1b7b2` — local singularity/backdrive promoted

The live semantic family learns the `{1,2,3,4}` permutation schema from visible training outputs. The predictor intersects row and column fibers, commits only singleton intersections, and iterates. The real held-out 4x4 grid is recovered without branch search in the regression fixture.

### P0002 `27f8ce4f` — first 0/20 transfer repair

All four demonstrations support one generic macro rule:

> Let `m` be the modal color of the 3x3 input. For every macro position whose source cell equals `m`, stamp a complete copy of the input into that 3x3 output block; make every other block uniformly blank.

The trigger varies across the four demonstrations (`8`, `7`, `5`, `9`), so this is not a fixed-color task patch. On the held-out input the mode is `7`; the source positions containing `7` are exactly the active macro blocks in the target.

A source-pinned full-task regression now requires the live learner to return the exact held-out answer with `modal_macro_stamp`.

### P0002 `84f2aca1` and `00dbd492` — one geometry family, two old failures

These two tasks reveal a reusable object-geometry separator.

For `84f2aca1`, hollow rectangular frames obey:

```text
interior area 1 -> fill 5
interior area 2 -> fill 7
```

independently of frame boundary color.

For `00dbd492`, color-2 rectangular frames obey:

```text
interior area 9  -> fill 8
interior area 25 -> fill 4
interior area 49 -> fill 3
```

and embedded interior color-2 markers must remain unchanged.

The same generic `RectangularEnclosureAreaFill` implements both by filling only background cells in a recognized frame interior. Independent exact replays match both held-out targets. Regression fixtures cover the actual 84f test layout and the marker-preservation behavior from 00db.

## Failure/guardrail retained: `f3e62deb`

At the natural `color -> movement direction` interface, training supports `8 -> right` and `6 -> up` but the tests introduce unseen colors `4` and `3`. Multiple mappings agree on all training facts and disagree on those test cases. Therefore this interface has no prediction singularity.

The correct status remains `UNKNOWN`, not a fabricated zero or forced direction, unless another justified semantic interface or learned cross-task prior resolves it.

## What is validated versus not yet validated

### Independently replayed exact

Compact exact Python replays performed during development reproduced:

- `a85d4709` marker-column mapping;
- `d037b0a7` downward propagation;
- `007bbfb7` both surviving macro/micro descriptions with learned blank `0`;
- ARC2 `4cd1b7b2` singleton intersection/backdrive;
- P0002 `27f8ce4f` modal-macro stamping;
- P0002 `84f2aca1` rectangle-area filling;
- P0002 `00dbd492` rectangle-area filling including preservation of embedded markers.

### Committed regression coverage

- `tests/test_semantic_callosal_interfaces_10.py`
- `tests/test_p0002_semantic_transfers_10.py`

### Not yet claimed

GitHub currently reports no registered status checks on these commits, and a full native repo pytest/packet rerun has not yet been observed through CI in this session. Therefore the claims above are mechanism-level exact replays plus committed regression specifications, not a claim that the historical P0001/P0002 packets have already been regenerated end-to-end under the new controller.

## Emerging principle

The strongest result is not the raw number of repaired tasks. It is that old failures are beginning to cluster by **missing separator type**:

```text
raw pixel relation fails
    -> coordinate quotient        (a85d4709)
    -> procedural/run state       (d037b0a7)
    -> macro/micro quotient       (007bbfb7, 27f8ce4f)
    -> overlapping CSP fibers     (4cd1b7b2)
    -> topology                   (00d62c1b)
    -> object geometry            (84f2aca1, 00dbd492)
    -> unsupported semantic state (f3e62deb: remain UNKNOWN)
```

This is the operational form of forward/backward singularity learning for ARC: propose the smallest semantic crossing state that makes the training-side forward and backward views one exact compatible object; use contradictions and residual topology to decide which kind of state to add; and stop when surviving global hypotheses collapse to one externally relevant prediction rather than requiring a unique latent explanation.
