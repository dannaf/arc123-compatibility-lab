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

## Trace discipline

Every trace event is an explicit observable artifact: action name, selected scope, generic hypothesis parameters, prediction coverage, support state, residual count, and counterexample coordinate. The trace is not a proxy for hidden model chain-of-thought.

## Current negative evidence

P0001's initial grammar succeeds on a row-span fill but fails three other curated tasks. P0002 then records a complete, no-abstention `0/20` ARC1+ARC2 baseline. A generic `repeat_tile` operator passes a synthetic inference/answer test but P0003's pre-registered non-overlapping `0/20` cohort does not demonstrate transfer. These failures distinguish missing generic operator families from future ranking, parameter-binding, or search problems. They must not be converted into a task-specific `_fit_algorithm_*` response.
