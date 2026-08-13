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
- `P0012-ARC12-SELF-MASK-MACRO-STAMP-CURATED-60` adds an input-relative macro-stamp family and reaches `8/60` on the same curated development roster (`+4` over P0011). It is development evidence only, not a transfer or solver claim.
- `P0013-ARC12-FRESH-FILENAME-FROZEN-50` freezes the P0012-era controller/evaluator bytes and a new source-pinned filename-only 25+25 cohort before selected JSON is decoded. It is `0/50` exact, with all 50 complete NO reports retained. This negative holdout result rules out any ARC1/ARC2 solver claim for the current vocabulary.
- `P0014-ARC12-DEVELOPMENT-BASELINE-40` freezes a disjoint filename-only 20+20 development roster and its pre-change controller: `2/40` exact, with every complete NO retained and source-pinned reproducibility verified.
- `P0015-ARC12-AXIS-MODE-DENOISE-DEVELOPMENT-40` adds a generic, per-input row/column modal-support denoising relation. It is synthetically validated but remains `2/40` on the same P0014 roster (`+0`); no transfer or solver capability is claimed.
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
python3 scripts/run_arc12_tiny_rediscovery.py --verify \
  --packet research/packets/P0012_ARC12_SELF_MASK_MACRO_STAMP_CURATED_60.json \
  --report-root reports/P0012_arc12_self_mask_macro_stamp_curated_60 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0013_ARC12_FRESH_FILENAME_FROZEN_50.json \
  --report-root reports/P0013_arc12_fresh_filename_frozen_50 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0014_ARC12_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0014_arc12_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0015_ARC12_AXIS_MODE_DENOISE_DEVELOPMENT_40.json \
  --report-root reports/P0015_arc12_axis_mode_denoise_development_40 \
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

The source check requires clean detached revisions specified in the packet. P0013's controller bytes are intentionally historic, so verify it from a clean worktree at `df56d6b8c9a3da62e4f42c08e40d5ff6c31c6dc2`, not after newer controller-source changes. `--run` writes a report, explicit JSON trace, native SVG corpus-callosum diagram, complete prediction, and post-answer verdict for every task.

## Repository map

- `src/arc123/` — generic perception, hypothesis, persistent theory, compatibility, controller, trace, and adapter code.
- `research/cohorts/` — source-pinned ARC12 curriculum/generalization metadata.
- `research/oracle_specs/` and `research/oracle_materializations/` — offline-only observable schemas and source-pinned pilot/audit outputs.
- `reports/` — retained ARC12 reports through P0015, including complete development and frozen-holdout V&V evidence.
- `docs/` — architecture, validation, oracle, and visualization protocol.
