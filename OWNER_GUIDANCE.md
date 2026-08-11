# Owner Guidance and Implementation Boundary

## Authoritative owner record

The verbatim owner guidance is intentionally preserved in [SingularityML issue #3542](https://github.com/dannaf/SingularityML/issues/3542). This repository does not paraphrase it as a replacement source. [Issue #3541](https://github.com/dannaf/SingularityML/issues/3541) is the developed technical interpretation and implementation tracker.

## Implemented interpretation

ARC1/ARC2 are treated as **latent-interactive** learning episodes: demonstrations are parallel evidence worlds, hypothesis operations are internal actions, observed agreement/residual/counterexample is feedback, and held-out test output is post-answer evaluation only. ARC3 uses the same learner state with external actions and transitions.

The intended core remains corpus-callosum factorization, probabilistic compatibility, exact support/hidden-zero discipline, singularity learning, incremental representation growth, and wavefunction-style collapse. In code this means:

1. generic perceptions and transforms are explicit;
2. a partial theory may retain UNKNOWN cells and survive without contradiction;
3. an observed contradiction yields exact zero support for that hypothesis assertion;
4. compatible complete theories are grouped by their complete test predictions and collapsed with an inspectable score;
5. every attempted task emits a complete grid and a durable YES/NO V&V report.

## Non-negotiable boundaries

- Do not use historical task-shaped schemas, feature contracts, or GT solver code as live answer mechanisms.
- Do not use held-out test output until a complete prediction is committed.
- Keep ARC2-GT Claude-owned/read-only; this repository only consumes detached source pins for V&V.
- Keep historical schemas and decomposition mappings as offline oracle/debug artifacts only.
- Retain failures in denominators; no silent abstention, task deletion, or benchmark submission.
- Record explicit observable actions/evidence/revisions, not private chain-of-thought.

## Current phase

P0001 establishes the core with simple generic transformations and a source-pinned tiny curated packet. It has not solved ARC1 or ARC2. The next work is to grow generic perceptions/hypothesis operators from retained counterexamples, rerun the curated 60 blind, then freeze and evaluate the disjoint 50.
