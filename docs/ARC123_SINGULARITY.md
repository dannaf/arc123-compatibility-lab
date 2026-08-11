# ARC123 Singularity

ARC123 uses one learning loop in two observational forms:

```text
perceive → attend → propose → apply → compare → find counterexample
        → refine/specialize/generalize/compose → retest → commit
```

For ARC1/ARC2 the operations are internal and reversible. Each demonstration is a queryable evidence world; its visible output defines constraints but does not make a test target available. For ARC3 the same operations include external actions whose transitions provide causal evidence.

The corpus callosum is the compatibility interface between perceived evidence and candidate explanatory actions. It must preserve uncertainty: support not observed is unknown; only an explicit failed prediction is impossible. This lets an agent preserve a useful local theory while it explains only part of a grid, then compose it rather than discarding it as an all-or-nothing one-shot program.

The initial implementation is deterministic planning/search. Policy learning may later improve which demo, region, or hypothesis action is selected, but a learned policy must be evaluated independently from oracle answer leakage.
