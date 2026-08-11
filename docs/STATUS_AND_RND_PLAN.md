# ARC123 Status and R&D Plan

## Current evidence

| Packet | Scope | Exact post-answer result | Interpretation |
| --- | --- | ---: | --- |
| P0001 | Four curated pilot tasks | 1/4 | A generic row-span-fill theory can be learned from demonstrations and collapsed into a complete answer. |
| P0002 | Initial 10 ARC1 + 10 ARC2 filename-only curated cohort | 0/20 | The initial grammar is far too small; every task still has a complete V&V-backed NO report. |
| P0003 | Non-overlapping 10 ARC1 + 10 ARC2 transfer cohort | 0/20 | The added generic `repeat_tile` primitive passes synthetic tests but has no demonstrated transfer in this cohort. |

There are 44 retained task attempts. Every one has a committed full grid, explicit YES/NO all-cell validation, learning trace, and native corpus-callosum SVG. There are no abstentions and no discarded failures.

## What has been validated

- The live controller uses only training input/output evidence plus a test input. Historical ARC12 schemas, GT feature contracts, task IDs, GT solver code, decompositions, and test targets are outside its answer-selection interface.
- A static ARC task can operate as an `ARC12InteractiveEnv`: demonstrations are parallel evidence worlds and attention/propose/compare/counterexample/commit are observable internal actions.
- Compatibility preserves `UNKNOWN != IMPOSSIBLE`; observed contradiction receives exact zero support while incomplete partial theories remain explicit rather than being treated as failure.
- Brain-surgery reports are deterministic artifacts. The packet verifier reproduces the complete output directory, not merely the top-level score receipt.

## What is not validated

- No ARC-AGI-1 or ARC-AGI-2 solver claim is justified. The only real curated success is P0001's 1/4 pilot result; neither 10+10 cohort has a successful answer.
- The generic grammar does not yet cover object selection, bounding-box crop/extraction, region filling, structured repetition, panel relations, or multi-step composition at the required breadth.
- P0002/P0003 are curated-development evidence, not the frozen 25+25 generalization denominator.

## Next gated work

1. Add only generic, independently testable perception/action families: component correspondence, frame/interior masks, crop/extract, periodic repetition, and panel-aware relation binding. Do not add a task-ID branch or `_fit_algorithm_*` fitter.
2. For each candidate family, first add a synthetic unit contract and a trace-level counterexample test. Register its provenance and reuse expectation before it reaches a real ARC packet.
3. Freeze each packet's operator vocabulary so old reports reproduce even when later generic primitives are added.
4. Evaluate each promoted family on a new filename-only, non-overlapping curated cohort. Retain every failure and distinguish development replay from fresh transfer.
5. After credible curated-60 rediscovery progress, freeze the learner and evaluate the unchanged ARC12 disjoint 25 ARC1 + 25 ARC2 denominator. No frozen target may guide grammar changes.
6. Normalize ARC3 observable trajectories into the shared external-action trace schema, preserving SingularityML's oracle-isolation guard; use oracle assets only after blind play for V&V.

## Promotion rule

A primitive is reusable only after it has: a generic definition, deterministic unit and mutation checks, at least one task-independent transfer result, a complete diagram/receipt, and no test-target access in the live controller. Otherwise it remains experimental evidence, not a solver capability.
