# Iterative Hypothesis Learning

## Controller contract

1. Attend to a demonstration/region with visible residual information.
2. Propose typed generic relations rather than a task ID or a complete historical schema.
3. Apply a hypothesis to every training pair.
4. Compare asserted cells with visible training outputs.
5. Preserve partial compatible hypotheses with UNKNOWN cells.
6. Record a concrete counterexample and reject only contradicted assertions.
7. Specialize, generalize, or compose at a generic operator level.
8. Collapse only training-compatible complete predictions and commit a full test grid.

## Persistent theory and revision

The default learner carries an immutable `PartialTheory` through a bounded frontier rather than treating each proposal as a disposable complete predictor. A theory records ordered rules, parameter bindings, scope predicates, per-demonstration assertions, explained/residual masks, UNKNOWN cells, support facts, counterexamples, and a revision history.

When a rule contradicts visible evidence, the learner preserves the surviving theory and turns the counterexample into its next operation: it changes the rule's scope, adds a residual rule, or composes an independent generic rule. Scope predicates are perception-derived (`color_equals`, component area/rank, or border membership), not task identifiers. The frontier chooses another demonstration by unresolved residual coverage before retesting the revised theory.

`StagedCandidateBaseline` is retained only as the frozen implementation for `P0001`–`P0003`, whose reports must remain byte-reproducible. It is not the architecture under current development.

## Trace discipline

Every trace event is an explicit observable artifact: action name, selected scope, generic hypothesis parameters, prediction coverage, support state, residual count, and counterexample coordinate. The trace is not a proxy for hidden model chain-of-thought.

## Current evidence and limits

Synthetic revision tests now verify retained scoped rules, multi-rule composition, dynamic demonstration selection, perception-derived scope predicates, and input-derived dihedral/blank macro tiling. They establish the state-transition mechanism, not ARC1/ARC2 task coverage.

P0001's initial grammar succeeds on a row-span fill but fails three other curated tasks. P0002 then records a complete, no-abstention `0/20` ARC1+ARC2 baseline. A generic `repeat_tile` operator passes a synthetic inference/answer test but P0003's pre-registered non-overlapping `0/20` cohort does not demonstrate transfer. P0005 begins the persistent-theory measurement at `1/60`; P0006 adds one generic residual dihedral-tile family and reaches `4/60`, while retaining every complete NO result. These packets are development evidence, not a solver score. The final curated acceptance bar remains open until independent review and broader transfer support it. Failures must not be converted into a task-specific `_fit_algorithm_*` response.
