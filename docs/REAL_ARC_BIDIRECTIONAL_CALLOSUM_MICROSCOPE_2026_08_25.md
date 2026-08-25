# Real ARC bidirectional corpus-callosum microscope — 2026-08-25

Related: #6, #7, `dannaf/SingularityML#3659`

## Owner request — verbatim

> Did you attempt this on some example ARC-AGI-1/2 tasks, eg 007?---please do so now

## Bottom line

Yes. The new shared-joint / forward-backward formulation was exercised on real ARC tasks rather than only synthetic fixtures.

The packet now contains:

- `research/experiments/bidirectional_callosum_real_arc_microscope.py`
- `research/experiments/bidirectional_callosum_real_arc_results.json`
- `research/experiments/bidirectional_callosum_arc2_latin_microscope.py`
- `research/experiments/bidirectional_callosum_arc2_latin_results.json`

The two most informative cases are ARC-AGI-1 `007bbfb7` and official ARC-AGI-2 training task `4cd1b7b2`.

---

## 1. `007bbfb7`: original corpus-callosum rule, now bidirectional

The historical corpus-callosum solution uses two input-side readings for each 9x9 output cell:

```text
macro = input[r//3, c//3]
micro = input[r%3,  c%3]
```

and the task relation is the Kronecker/stamping rule. On the observed training distribution the exact callosal joint is

```text
M(macro, micro, output).
```

### Exact measured facts

Pooling all five training examples gives:

- 405 output-cell observations;
- 13 observed `(macro,micro)` contexts;
- 13 positive joint support cells `(U,Y)`;
- the forward conditional `P(Y | macro,micro)` is deterministic for every observed context.

The reverse conditional is **not** an inverse function.

For every nonzero training output color `c`:

```text
P((macro,micro)=(c,c) | Y=c) = 1.
```

But for `Y=0`, nine different causes survive:

```text
(0,0), (0,2), (0,4), (0,6), (0,7),
(2,0), (4,0), (6,0), (7,0).
```

The exact empirical reverse probabilities are recorded in the results JSON. Thus this fixture validates the intended semantics:

> deterministic forward corpus-callosum conditional does not imply a deterministic backward inverse; both are valid disintegrations of one shared crossing joint.

### Prediction singularity without program singularity

A small generic candidate family was checked using training evidence only:

```text
tile
scale_macro
micro_if_macro_nonzero
macro_if_micro_nonzero
```

The two gated rules both survive the five demonstrations. Because each example uses one nonzero color, they are observationally equivalent on this task. Therefore:

```text
program singularity:    NO   (two symbolic programs survive)
prediction singularity: YES  (one complete test prediction group)
```

The unique prediction group was committed and then compared to the held-out test output: **exact match**.

This is a concrete example of why ARC need not identify one unique internal explanation before acting/answering.

---

## 2. `4cd1b7b2`: ARC-AGI-2 local forward/backward singularity

This official ARC-AGI-2 training task is particularly useful because the bidirectional mechanism itself performs nontrivial inference.

Across all three demonstrations, the output:

1. preserves every nonzero input clue;
2. completes every row to a permutation of `{1,2,3,4}`;
3. completes every column to a permutation of `{1,2,3,4}`.

The experiment treats these as a training-derived semantic schema.

For each missing cell `(r,c)` define two local supports:

```text
F_rc = digits missing from row r
B_rc = digits missing from column c
```

and the callosal compatibility fiber

```text
C_rc = F_rc ∩ B_rc.
```

A local singularity occurs when `|C_rc|=1`. That value is committed and immediately backdriven into all incident row/column supports.

### Why this is genuinely bidirectional

The held-out test input is:

```text
0 1 2 3
0 3 1 0
3 0 4 1
0 4 0 2
```

Initially, examples include:

```text
cell (1,0): row support    {2,4}
            column support {1,2,4}
            intersection   {2,4}   -- not yet singular

cell (3,0): row support    {1,3}
            column support {1,2,4}
            intersection   {1}     -- singular only by matching both sides
```

Other cells are singular from one or both directions. As singleton intersections are committed and backdriven, the previously ambiguous `(1,0)` fiber contracts to one value as well.

The process collapses all six missing cells without branching and produces:

```text
4 1 2 3
2 3 1 4
3 2 4 1
1 4 3 2
```

Only after this complete prediction was formed was the held-out target consulted. Result: **exact match**.

All three training examples are likewise solved exactly by the same intersection/backdrive procedure.

This is the cleanest concrete ARC evidence so far for the new formulation:

> two locally incomplete directional models can meet at a small separator, and exact local compatibility plus backdrive can collapse the correct value without centralized enumeration of all complete grids.

For this 4x4 case, of course, the underlying Latin-square CSP is easy and tiny; no complexity claim follows. The point is the mechanism.

---

## 3. Additional `d037b0a7` directional control

The earlier repo's ARC2-labelled rediscovery packet contains `d037b0a7` (also an original ARC-AGI-1 training task and carried into the ARC-AGI-2 training corpus).

A small generic directional family was checked:

```text
identity  -> 0/3 exact train examples
fill_up   -> 0/3
fill_down -> 3/3
fill_both -> 0/3
```

So `fill_down` reaches program singularity in that family. It predicts the held-out output exactly.

Its training-side reverse relation is also exact: collapse each constant downward color-run to its first nonzero marker. This reconstructs all three training inputs exactly. The test reverse also reconstructs the input post-V&V.

This is a useful directional control, but `4cd1b7b2` is the stronger bidirectional-local example because neither local side alone always determines the answer.

---

## 4. What was and was not accomplished

### Accomplished

- exercised the new shared-callosal-joint semantics on real ARC data;
- verified a deterministic-forward / non-invertible-backward case on `007bbfb7`;
- demonstrated prediction singularity without program singularity on `007bbfb7`;
- demonstrated exact local support intersection + backdrive on an official ARC-AGI-2-new task;
- obtained the exact ARC2 held-out grid without branch search in the `4cd1b7b2` microscope;
- preserved the train/test leakage boundary in the experiment design;
- produced exact executable fixtures and machine-readable results.

### Not accomplished

This is not yet a generic ARC solver. In particular:

- the semantic candidate families used in the microscopes are small and hand-chosen;
- the ARC2 Latin/permutation schema is detected/verified from demonstrations, but the live IHL controller does not yet autonomously invent that schema from its full generic perception/operator language;
- no claim is made that arbitrary ARC tasks admit singleton local forward/backward collapse;
- no polynomial generality theorem follows from the 4x4 Latin example.

The next decisive step is therefore **autonomous semantic-interface discovery**: make the normal ARC123 learner itself propose row/column all-different, macro/micro, propagation, object-relation, bridge, and other procedural states from counterexample topology, then let the bidirectional compatibility layer select/refine them rather than preselecting the microscope family.
