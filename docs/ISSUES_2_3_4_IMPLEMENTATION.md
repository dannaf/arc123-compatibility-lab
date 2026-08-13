# Issues 2, 3, and 4: Implementation Record

This record maps the implementation to the three architecture blockers without upgrading evidence beyond what has been reproduced.

## Issue 2 — persistent iterative partial theory

[Issue #2](https://github.com/dannaf/arc123-compatibility-lab/issues/2) is addressed in code by `PartialTheory` and the default `IterativeHypothesisLearner`.

- A theory retains ordered rules, scopes, bindings, partial predictions, explained and residual masks, support, counterexamples, UNKNOWN state, and revision history.
- A contradiction drives a theory-changing operation: scope specialization, residual rule addition, or rule composition. It does not discard the useful part of a theory just because one assertion failed.
- The controller uses a bounded, scored frontier of theory states and dynamically selects further demonstrations by residual coverage.
- The tests cover scope-preserving counterexample revision, multi-rule composition, a discriminating second demonstration, and perception-derived scopes.

The issue's final curated acceptance condition is **not claimed complete**. `P0005-ARC12-PERSISTENT-THEORY-CURATED-60` establishes the initial persistent-theory measurement at `1/60`; `P0006-ARC12-RESIDUAL-DIHEDRAL-TILE-CURATED-60` reaches `4/60`; and `P0012-ARC12-SELF-MASK-MACRO-STAMP-CURATED-60` reaches `8/60` on that same development roster. The P0012 additions are generic relative-selector macro relations, but they are not independent transfer evidence. The subsequently frozen, source-byte-pinned, filename-only `P0013-ARC12-FRESH-FILENAME-FROZEN-50` result is `0/50` exact. All 50 failures remain complete V&V-backed reports. The current vocabulary therefore does not meet the issue's generalization requirement, and this blocker must remain open.

## Issue 3 — benchmark-neutral shared core

[Issue #3](https://github.com/dannaf/arc123-compatibility-lab/issues/3) is addressed by the neutral contracts in `src/arc123/contracts.py` and both ARC12/ARC3 adapters.

- ARC12 presents visible training pairs as parallel `ObservationWorld` evidence.
- ARC3 presents a source-pinned public action transition through the same observation, hypothesis-action, environment-action, feedback, compatibility, residual, and trace types.
- `P0004-ARC3-REAL-TRANSITION-PROBE` starts with an empty theory store, makes an external probe, observes a real recorded state change, revises its mechanics hypothesis, and takes a second accepted action.
- The adapter exposes neither provenance nor future actions to the agent and refuses unmatched actions rather than simulating outcomes.

The P0004 report is a reproducible shared-core transition experiment, not a game-playing or ARC3-solver result. A blind live public-game session remains the next required evidence before any ARC3-solving claim.

## Issue 4 — offline oracle/GT materialization

[Issue #4](https://github.com/dannaf/arc123-compatibility-lab/issues/4) is addressed by two validated, source-pinned offline manifests:

- [`ARC12_IHL_GT_PILOT_001.json`](../research/oracle_materializations/ARC12_IHL_GT_PILOT_001.json) is a four-record ARC12 pilot that quarantines generic decomposition metadata from all live runs.
- [`ARC3_IHL_GT_INVENTORY_001.json`](../research/oracle_materializations/ARC3_IHL_GT_INVENTORY_001.json) inventories 121 audited SingularityML assets in the required five categories and records reuse-versus-new-annotation decisions.
- `scripts/materialize_oracle_lane.py` reproduces both manifests from source pins.
- Isolation tests verify that no live adapter/controller import reads the materialization module and that forbidden oracle/final-rule paths are rejected.

## Reproducible V&V

```bash
python3 -m unittest discover -s tests -v
python3 scripts/materialize_oracle_lane.py \
  --arc12-root /path/to/arc12-compatibility-lab \
  --arc12-commit 525000ab1f78fb1e66906149f72f6e8eac34ab71 \
  --singularityml-root /path/to/SingularityML \
  --singularityml-commit d32b91e6b442079fbd46f0cd17c608485032d278
python3 scripts/run_arc3_real_transition_probe.py --verify \
  --singularityml-root /path/to/SingularityML
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
```

The native P0004 SVG is visually reviewed as part of the packet check. It shows the actual before/after transition, red outlines for observed changed cells, two explicit external actions, and the initial/final mechanics hypotheses.
