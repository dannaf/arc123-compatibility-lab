# Dataset and Oracle Plan

## ARC12-IHL-GT

`ARC12-IHL-GT` is an offline dataset of structured, externally reportable hypothesis trajectories over the curated 60. It may contain observations, candidate hypotheses, explicit predictions, checked evidence, counterexamples, revisions, residual summaries, and final verification. It must not depend on inaccessible/private chain-of-thought.

The [curated 60](../research/cohorts/ARC12_COHORT_IMPORT_001.json) is the rediscovery curriculum. Historical selected schemas and generic decomposition mappings remain debug/oracle artifacts; they cannot be inputs to blind controller runs. The frozen 25+25 is disjoint and remains a post-development generalization lane.

The first source-pinned pilot is [`ARC12_IHL_GT_PILOT_001.json`](../research/oracle_materializations/ARC12_IHL_GT_PILOT_001.json). It contains four representative records (two ARC1 and two ARC2) with externally reportable generic-decomposition fields only. It intentionally omits answer grids, hidden reasoning, and all live-learner access.

## ARC3-IHL-GT

`ARC3-IHL-GT` normalizes observable human/action traces, public game transitions, and post-hoc oracle comparisons into the same high-level action/evidence schema. Existing SingularityML trajectory and oracle assets must be audited by source pin before annotation; final rules/actions are useful validation material but are not automatically reasoning trajectories.

[`ARC3_IHL_GT_INVENTORY_001.json`](../research/oracle_materializations/ARC3_IHL_GT_INVENTORY_001.json) is the first machine-readable audit. It pins both the SingularityML audit document and the underlying audited asset snapshot, classifies every reviewed path as observable trajectory, annotation, post-hoc oracle, video-only material, or unsuitable/leaky, and records whether reuse is possible or a new annotation pass is required.

## Oracle boundary

Frontier models or humans may create concise external annotations such as `observation`, `candidate hypothesis`, `prediction`, `evidence checked`, `counterexample`, and `revision`. They may not provide hidden reasoning-token access, test targets to the live agent, or task-specific answer dispatch.

Materialization occurs only through `scripts/materialize_oracle_lane.py`. It is an offline build step: `src/arc123/oracles.py` is excluded from live adapter/controller imports, and tests reject oracle, final-rule, diff, reasoning, decomposition, feature, and GT paths in the live ARC3 transition adapter.
