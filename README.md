# ARC123 Compatibility Lab

An evidence-gated research repository for one **Iterative Hypothesis Learning (IHL)** core shared across ARC-AGI-1, ARC-AGI-2, and ARC-AGI-3.

## Governing direction

- [Owner guidance, preserved verbatim](https://github.com/dannaf/SingularityML/issues/3542)
- [Technical ARC123 design tracker](https://github.com/dannaf/SingularityML/issues/3541)
- [ARC12 evidence handoff](https://github.com/dannaf/arc12-compatibility-lab/issues/4)

The live learner receives demonstrations and a test input, builds/revises explicit generic hypotheses, and commits a complete output. Historical ARC12 schemas, GT feature contracts, GT solvers, task IDs, and held-out test targets are never live answer-selection inputs.

## Current status

- `P0001-ARC12-TINY-REDISCOVERY` is reproducible against detached ARC1/ARC2 source pins.
- The initial non-VLM controller solves `1/4` curated development attempts post-answer and retains all three complete-answer failures with YES/NO V&V.
- The result is a first architecture test, **not** an ARC1, ARC2, or ARC3 completion claim.
- The 60-task curated curriculum and frozen disjoint 25+25 denominator are imported by immutable [ARC12 handoff pins](research/cohorts/ARC12_COHORT_IMPORT_001.json).

## Run P0001

```bash
python3 -m unittest discover -s tests -v
python3 scripts/run_arc12_tiny_rediscovery.py --run \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_tiny_rediscovery.py --verify \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
```

The source check requires clean detached revisions specified in the packet. `--run` writes a report, explicit JSON trace, native SVG corpus-callosum diagram, complete prediction, and post-answer verdict for every task.

## Repository map

- `src/arc123/` — generic perception, hypothesis, compatibility, controller, trace, and adapter code.
- `research/cohorts/` — source-pinned ARC12 curriculum/generalization metadata.
- `research/oracle_specs/` — offline, observable annotation schemas only.
- `reports/` — retained P0001 brain-surgery reports and packet receipts.
- `docs/` — architecture, validation, oracle, and visualization protocol.
