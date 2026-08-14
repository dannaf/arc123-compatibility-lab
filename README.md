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
- `P0016-ARC12-DEVELOPMENT-BASELINE-40` freezes a second, disjoint filename-only 20+20 development roster and its pre-change controller: `0/40` exact, all complete NO reports retained.
- `P0017-ARC12-SELF-CONTAINED-SUBSET-CROP-DEVELOPMENT-40` adds a generic unique-minimum color-subset crop relation. It is synthetically validated but remains `0/40` on P0016's roster (`+0`); no transfer or solver capability is claimed.
- `P0018-ARC12-DEVELOPMENT-BASELINE-40` freezes a third, disjoint filename-only 20+20 development roster before a component/bounding-box portfolio change: `3/40` exact (`2` ARC1, `1` ARC2), with all `37` complete NO reports retained and reproducible.
- `P0019-ARC12-FRAME-PANEL-GEOMETRY-DEVELOPMENT-40` adds guarded frame-interior extraction and central-separator cellwise composition on P0018's frozen roster: `5/40` exact (`+2`, both ARC1), with all `35` complete NO reports retained and reproducible. This is same-cohort development evidence only.
- `P0020-ARC12-DEVELOPMENT-BASELINE-40` freezes a fourth disjoint filename-only 20+20 cohort after the P0019 checkpoint: `4/40` exact (`3` ARC1, `1` ARC2), including three cross-cohort central-separator selections. Every `36` complete NO report is retained; this is a limited disjoint development replication, not a solver claim.
- `P0021-ARC12-BILATERAL-SCALE-DEVELOPMENT-40` compares two guarded input-derived relations against P0020's frozen controller on the same fourth cohort: `6/40` exact (`+2`; one ARC1 adjacent-bilateral pair table and one ARC2 dynamic non-background-color scale), with all `34` complete NO reports retained and reproducible. This is same-cohort development evidence only.
- `P0022-ARC12-BILATERAL-SCALE-TRANSFER-50` freezes a new filename-only 25+25 transfer cohort excluding every prior imported, frozen, and development roster: `3/50` exact (`2` ARC1, `1` ARC2), with all `47` complete NO reports retained and reproducible. The ARC2 exact result uses the guarded adjacent-bilateral relation on an unseen task; this is limited primitive-level transfer evidence, not a solver claim.
- `P0023-ARC12-DEVELOPMENT-BASELINE-40` freezes a fifth disjoint filename-only 20+20 development cohort after P0022: `3/40` exact (`3` ARC1, `0` ARC2), with all `37` complete NO reports retained and reproducible. It is the immutable pre-change denominator for the next generic portfolio, not a solver claim.
- `P0024-ARC12-PANEL-STREAM-FRACTAL-DEVELOPMENT-40` adds three new generic exact selections on P0023's fixed roster—separated-panel visible tuple combination, reflective quadrant crop, and uniform-block self-stamping—and reaches `6/40` (`+3`; `5` ARC1, `1` ARC2). All `34` complete NO reports remain retained. This is same-cohort development evidence only.
- `P0025-ARC12-HIDDEN-ZERO-STREAM-DEVELOPMENT-40` corrects the anti-diagonal stream relation to learn a shared hidden background from visible training outputs instead of assuming it is modal in every input. It reaches `7/40` (`+1`; `6` ARC1, `1` ARC2) on P0023's roster, with all `33` complete NO reports retained. The P0024 post-answer failure informed this correction, so it is explicitly post-hoc development evidence, not transfer or a solver claim.
- `P0026-ARC12-HIDDEN-ZERO-TRANSFER-50` freezes the P0025 vocabulary on a new filename-only 25+25 cohort excluding every earlier imported, development, and transfer task: `4/50` exact (`2` ARC1, `2` ARC2), with all `46` complete NO reports retained. It independently reuses adjacent-bilateral, central-separator, and dihedral-tile relations; none of P0024/P0025's new operators select. This is limited whole-vocabulary transfer evidence, not a solver claim.
- `P0027-ARC12-DEVELOPMENT-BASELINE-40` freezes a sixth disjoint filename-only 20+20 development cohort after P0026: `3/40` exact (`1` ARC1, `2` ARC2), with all `37` complete NO reports retained and reproducible. It is the immutable pre-change denominator for the next generic portfolio, not transfer or a solver claim.
- `P0028-ARC12-COMPATIBILITY-PORTFOLIO-DEVELOPMENT-40` evaluates the frozen P0028 vocabulary on P0027's same cohort: `8/40` exact (`+5`; `4` ARC1, `4` ARC2), with all `32` complete NO reports retained. The new exact selections use visible-evidence translation, total-palette scaling, odd-quadrant extraction, singleton-to-border projection, and count-conditioned line generation. This is post-hoc same-cohort development evidence only, not transfer or a solver claim.
- `P0029-ARC12-COMPATIBILITY-PORTFOLIO-TRAINING-TRANSFER-50` freezes the unchanged P0028 controller on a fresh filename-only `25 ARC1 + 25 ARC2` all-training-split cohort because only ten unseen ARC2 evaluation filenames remain. It is `4/50` exact (`3` ARC1, `1` ARC2), with all `46` complete NO reports retained and reproduced byte-for-byte. Every YES is an existing rotation/dihedral-tile relation; none of P0028's new relations selects on this fresh cohort. This is limited all-training-subset transfer evidence, not an ARC1/ARC2 solver claim.
- `P0030-ARC12-DEVELOPMENT-BASELINE-40` freezes the unchanged P0028 controller on a seventh disjoint filename-only 20+20 development roster: `2/40` exact (`0` ARC1, `2` ARC2), with all `38` complete NO reports retained and reproduced byte-for-byte. The two YES selections are existing dihedral-tile and central-separator relations. It is the immutable same-cohort pre-change denominator for the next bounded generic portfolio, not transfer or a solver claim.
- `P0031-ARC12-CONTIGUOUS-COMPONENT-DEVELOPMENT-40` compares two bounded generic compatibility relations on P0030's immutable roster: `4/40` exact (`+2`; `1` ARC1, `3` ARC2), with all `36` complete NO reports retained and reproduced byte-for-byte. The new exact selections are a conflict-free four-panel visible tuple table and duplicate-aware 4-connected component crop; this same-cohort development result is not transfer or a solver claim.
- `P0032-ARC12-CONTIGUOUS-COMPONENT-TRAINING-TRANSFER-50` freezes P0031's unchanged bytes on a fresh filename-only all-training `25 ARC1 + 25 ARC2` cohort: `4/50` exact (`2` ARC1, `2` ARC2), with all `46` complete NO reports retained and reproduced byte-for-byte. Every YES uses pre-existing central-separator or dihedral relations; neither P0031 relation selects. This is limited negative all-training-subset transfer evidence, not an ARC1/ARC2 solver claim.
- `P0033-ARC12-TRAINING-DEVELOPMENT-BASELINE-40` freezes P0031's unchanged generic vocabulary on a new disjoint filename-only all-training `20 ARC1 + 20 ARC2` development cohort: `3/40` exact (`1` ARC1, `2` ARC2), with all `37` complete NO reports retained and reproduced byte-for-byte. Every YES uses pre-existing dihedral, recolor, or central-separator relations; neither P0031 relation selects. This is a later exposed development baseline, not independent transfer or an ARC1/ARC2 solver claim.
- `P0034-ARC12-SHARED-BACKGROUND-PANEL-DEVELOPMENT-40` evaluates one dynamically rederived shared-background odd-panel crop relation on P0033's exposed immutable cohort: `4/40` exact (`+1`; `1` ARC1, `3` ARC2), with all `36` complete NO reports retained and reproduced byte-for-byte. The new ARC2 selection crops one uniquely shaped panel among repeated structural peers while refusing tied masks and background ambiguity. This is same-cohort development evidence only, not transfer or an ARC1/ARC2 solver claim.
- `P0035-ARC12-SHARED-BACKGROUND-PANEL-TRAINING-TRANSFER-50` freezes P0034's generic vocabulary on a fresh filename-only all-training `25 ARC1 + 25 ARC2` cohort: `3/50` exact (`2` ARC1, `1` ARC2), with all `47` complete NO reports retained and reproduced byte-for-byte. Every YES uses a pre-existing mirror, central-separator, or dihedral relation; the P0034 odd-panel crop does not select. This is limited negative all-training-subset transfer evidence, not an ARC1/ARC2 solver claim.
- `P0036-ARC12-TRAINING-DEVELOPMENT-BASELINE-40` freezes P0035's byte-identical generic vocabulary on a ninth disjoint filename-only all-training `20 ARC1 + 20 ARC2` development cohort: `2/40` exact (`1` ARC1, `1` ARC2), with all `38` complete NO reports retained and reproduced byte-for-byte. Both YES outcomes use pre-existing quadrant/central-separator relations; the P0034 odd-panel crop does not select. This is a later exposed development baseline, not transfer or an ARC1/ARC2 solver claim.
- `P0037-ARC12-CROSS-SEPARATOR-REFLECTION-DEVELOPMENT-40` evaluates one dynamically rederived cross-separator quadrant-reflection stamp on P0036's exposed immutable cohort: `3/40` exact (`+1`; `2` ARC1, `1` ARC2), with all `37` complete NO reports retained and reproduced byte-for-byte. The new ARC1 selection requires a uniform structural cross, one payload quadrant, three uniform peer quadrants, a unique payload color, and a deterministic reflected/recolored full stamp; it refuses ambiguity. This is same-cohort development evidence only, not transfer or an ARC1/ARC2 solver claim.
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
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0016_ARC12_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0016_arc12_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0017_ARC12_SELF_CONTAINED_SUBSET_CROP_DEVELOPMENT_40.json \
  --report-root reports/P0017_arc12_self_contained_subset_crop_development_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0018_ARC12_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0018_arc12_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0019_ARC12_FRAME_PANEL_GEOMETRY_DEVELOPMENT_40.json \
  --report-root reports/P0019_arc12_frame_panel_geometry_development_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0020_ARC12_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0020_arc12_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0021_ARC12_BILATERAL_SCALE_DEVELOPMENT_40.json \
  --report-root reports/P0021_arc12_bilateral_scale_development_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0022_ARC12_BILATERAL_SCALE_TRANSFER_50.json \
  --report-root reports/P0022_arc12_bilateral_scale_transfer_50 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0023_ARC12_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0023_arc12_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0024_ARC12_PANEL_STREAM_FRACTAL_DEVELOPMENT_40.json \
  --report-root reports/P0024_arc12_panel_stream_fractal_development_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0025_ARC12_HIDDEN_ZERO_STREAM_DEVELOPMENT_40.json \
  --report-root reports/P0025_arc12_hidden_zero_stream_development_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0026_ARC12_HIDDEN_ZERO_TRANSFER_50.json \
  --report-root reports/P0026_arc12_hidden_zero_transfer_50 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0027_ARC12_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0027_arc12_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0028_ARC12_COMPATIBILITY_PORTFOLIO_DEVELOPMENT_40.json \
  --report-root reports/P0028_arc12_compatibility_portfolio_development_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0029_ARC12_COMPATIBILITY_PORTFOLIO_TRAINING_TRANSFER_50.json \
  --report-root reports/P0029_arc12_compatibility_portfolio_training_transfer_50 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0030_ARC12_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0030_arc12_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0031_ARC12_CONTIGUOUS_COMPONENT_DEVELOPMENT_40.json \
  --report-root reports/P0031_arc12_contiguous_component_development_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0032_ARC12_CONTIGUOUS_COMPONENT_TRAINING_TRANSFER_50.json \
  --report-root reports/P0032_arc12_contiguous_component_training_transfer_50 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0033_ARC12_TRAINING_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0033_arc12_training_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0034_ARC12_SHARED_BACKGROUND_PANEL_DEVELOPMENT_40.json \
  --report-root reports/P0034_arc12_shared_background_panel_development_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0035_ARC12_SHARED_BACKGROUND_PANEL_TRAINING_TRANSFER_50.json \
  --report-root reports/P0035_arc12_shared_background_panel_training_transfer_50 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0036_ARC12_TRAINING_DEVELOPMENT_BASELINE_40.json \
  --report-root reports/P0036_arc12_training_development_baseline_40 \
  --arc1-source /path/to/arc1-source \
  --arc2-source /path/to/arc2-source
python3 scripts/run_arc12_filename_holdout.py --verify \
  --packet research/packets/P0037_ARC12_CROSS_SEPARATOR_REFLECTION_DEVELOPMENT_40.json \
  --report-root reports/P0037_arc12_cross_separator_reflection_development_40 \
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

The source check requires clean detached revisions specified in the packet. P0013's controller bytes are intentionally historic, so verify it from a clean worktree at `df56d6b8c9a3da62e4f42c08e40d5ff6c31c6dc2`; P0018's baseline bytes are frozen at `260c212129445d1ba4bbda8cfa42f62b41a3446d`; P0019's geometry bytes are frozen at `f7246acf27dccc88a12b065ed6e2dbc1461f177c`; P0020's baseline bytes are frozen at `e7c5bac56acb1119fcb305c1596edaa6966b043f`; P0021's bilateral/scale bytes are frozen at `15833b3826281b49f70da8b9c7b2060ca1f00b8b`; P0022's fresh-transfer and P0023 baseline bytes are frozen at `cf3ff72abc98d8c8654d50694ca18ce68700b3af` and `4a4f70ae1735568ad87d3f46c085f59effb95fd8`; P0024's portfolio, P0025's hidden-zero correction, P0026's transfer controller, P0027's baseline controller, and P0028/P0029/P0030's compatibility-portfolio bytes are frozen at `a232432be2bc34e3e1beed732717a9936c6dda2f`, `eac3e7967acfbc7142b551a5c336f506d5df5440`, `eac3e7967acfbc7142b551a5c336f506d5df5440`, `eac3e7967acfbc7142b551a5c336f506d5df5440`, `a12e6344822d9e423bcc9267f3dbc3b34e4c3502`, `a12e6344822d9e423bcc9267f3dbc3b34e4c3502`, and `a12e6344822d9e423bcc9267f3dbc3b34e4c3502`, respectively. After a later controller-source change, verify any historic packet from its matching clean worktree; source-pinned regression tests retain the historic-byte audit in the evolving branch. `--run` writes a report, explicit JSON trace, native SVG corpus-callosum diagram, complete prediction, and post-answer verdict for every task.

P0031's contiguous-panel/component controller bytes are frozen at `fd3ac79b5415d0f7b42747c5bff19829802ccde3`; P0033's all-training development-baseline bytes are frozen at `5de7928e61ab625be59abab70ce3570e018cbd2e`; P0034's shared-background panel bytes are frozen at `3e04e03086528da6a9a2107a08ebdb4f219bdae4`; P0035's transfer and P0036's development-baseline bytes are frozen at `e869c4842817624925e6576a1be9bb1f27399977`; P0037's cross-reflection bytes are frozen at `5593527a16a57bcc0925ae3692b0888f141452e3`.

## Repository map

- `src/arc123/` — generic perception, hypothesis, persistent theory, compatibility, controller, trace, and adapter code.
- `research/cohorts/` — source-pinned ARC12 curriculum/generalization metadata.
- `research/oracle_specs/` and `research/oracle_materializations/` — offline-only observable schemas and source-pinned pilot/audit outputs.
- `reports/` — retained ARC12 reports through P0037, including complete development and frozen-holdout V&V evidence.
- `docs/` — architecture, validation, oracle, and visualization protocol.
