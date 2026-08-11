# ARC123 Compatibility Lab

An evidence-gated research repository for one **Iterative Hypothesis Learning (IHL)** core shared across ARC-AGI-1, ARC-AGI-2, and ARC-AGI-3.

## Governing direction

- [Owner guidance, preserved verbatim](https://github.com/dannaf/SingularityML/issues/3542)
- [Technical ARC123 design tracker](https://github.com/dannaf/SingularityML/issues/3541)
- [ARC12 evidence handoff](https://github.com/dannaf/arc12-compatibility-lab/issues/4)

The live learner receives demonstrations and a test input, builds/revises explicit generic hypotheses, and commits a complete output. Historical ARC12 schemas, GT feature contracts, GT solvers, task IDs, and held-out test targets are never live answer-selection inputs.

## Current status

- The default `IterativeHypothesisLearner` now searches persistent `PartialTheory` states: rules, scopes, bindings, per-demo evidence, explained/residual masks, contradictions, and revision provenance survive across iterations. `StagedCandidateBaseline` is retained only to reproduce the frozen `P0001`–`P0003` packets unchanged.
- `P0001-ARC12-TINY-REDISCOVERY` is reproducible against detached ARC1/ARC2 source pins.
- The initial non-VLM controller solves `1/4` curated development attempts post-answer and retains all three complete-answer failures with YES/NO V&V.
- `P0002-ARC12-INITIAL-20` satisfies the requested first `10 ARC1 + 10 ARC2` reporting cohort: `0/20` exact, `20/20` complete NO answers, and no abstentions.
- `P0003-ARC12-CURATED-20-TILE-TRANSFER` is a filename-only, non-overlapping fresh 10+10 cohort after a generic `repeat_tile` primitive; it is also `0/20`, so that primitive has synthetic support but no demonstrated transfer yet.
- `P0004-ARC3-REAL-TRANSITION-PROBE` uses the same observation/action/revision contracts against two source-pinned, recorded public ARC3 transitions. It confirms a minimal external probe/revision/exploit loop; it explicitly makes **no ARC3 level-solved claim**.
- `P0005-ARC12-PERSISTENT-THEORY-CURATED-60` measures the new persistent-theory controller on all imported curated tasks: `1/60` exact, `59/60` committed complete NO answers, and a report/diagram/receipt for every attempt. It demonstrates the mechanism and its present coverage limit, not an ARC1/ARC2 solution.
- `P0006-ARC12-RESIDUAL-DIHEDRAL-TILE-CURATED-60` adds one generic residual-directed orientation/blank macro-tile family and reaches `4/60` exact, with all `56` failures retained. The three new exact tasks use explicit residual targeting and ordered composition; this is development evidence, not a benchmark-solver claim.
- Offline-only ARC12 pilot and ARC3 source-audit inventory manifests are materialized under `research/oracle_materializations/`; live adapters reject oracle/final-rule paths.
- The result is a first architecture test, **not** an ARC1, ARC2, or ARC3 completion claim.
- The 60-task curated curriculum and frozen disjoint 25+25 denominator are imported by immutable [ARC12 handoff pins](research/cohorts/ARC12_COHORT_IMPORT_001.json).
- The current status, failure accounting, and next gated experiments are in [the R&D plan](docs/STATUS_AND_RND_PLAN.md).

## Run Packets

```bash
python3 -m unittest discover -s tests -v
python3 scripts/run_arc12_tiny_rediscovery.py --run \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_tiny_rediscovery.py --verify \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_tiny_rediscovery.py --verify \
  --packet research/packets/P0002_ARC12_INITIAL_20.json \
  --report-root reports/P0002_arc12_initial_20 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_tiny_rediscovery.py --verify \
  --packet research/packets/P0003_ARC12_CURATED_20_TILE_TRANSFER.json \
  --report-root reports/P0003_arc12_curated_20_tile_transfer \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_tiny_rediscovery.py --verify \
  --packet research/packets/P0005_ARC12_PERSISTENT_THEORY_CURATED_60.json \
  --report-root reports/P0005_arc12_persistent_theory_curated_60 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_tiny_rediscovery.py --verify \
  --packet research/packets/P0006_ARC12_RESIDUAL_DIHEDRAL_TILE_CURATED_60.json \
  --report-root reports/P0006_arc12_residual_dihedral_tile_curated_60 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/materialize_oracle_lane.py \
  --arc12-root /path/to/arc12-compatibility-lab \
  --arc12-commit 525000ab1f78fb1e66906149f72f6e8eac34ab71 \
  --singularityml-root /path/to/SingularityML \
  --singularityml-commit d32b91e6b442079fbd46f0cd17c608485032d278
python3 scripts/run_arc3_real_transition_probe.py --verify \
  --singularityml-root /path/to/SingularityML
```

The source check requires clean detached revisions specified in the packet. `--run` writes a report, explicit JSON trace, native SVG corpus-callosum diagram, complete prediction, and post-answer verdict for every task.

## Repository map

- `src/arc123/` — generic perception, hypothesis, persistent theory, compatibility, controller, trace, and adapter code.
- `research/cohorts/` — source-pinned ARC12 curriculum/generalization metadata.
- `research/oracle_specs/` and `research/oracle_materializations/` — offline-only observable schemas and source-pinned pilot/audit outputs.
- `reports/` — retained P0001/P0002/P0003 baseline reports, P0004's real-transition report, and P0005/P0006 persistent-theory ARC12 reports.
- `docs/` — architecture, validation, oracle, and visualization protocol.
