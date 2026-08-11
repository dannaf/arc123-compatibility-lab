# Dataset and Oracle Plan

## ARC12-IHL-GT

`ARC12-IHL-GT` is an offline dataset of structured, externally reportable hypothesis trajectories over the curated 60. It may contain observations, candidate hypotheses, explicit predictions, checked evidence, counterexamples, revisions, residual summaries, and final verification. It must not depend on inaccessible/private chain-of-thought.

The [curated 60](../research/cohorts/ARC12_COHORT_IMPORT_001.json) is the rediscovery curriculum. Historical selected schemas and generic decomposition mappings remain debug/oracle artifacts; they cannot be inputs to blind controller runs. The frozen 25+25 is disjoint and remains a post-development generalization lane.

## ARC3-IHL-GT

`ARC3-IHL-GT` normalizes observable human/action traces, public game transitions, and post-hoc oracle comparisons into the same high-level action/evidence schema. Existing SingularityML trajectory and oracle assets must be audited by source pin before annotation; final rules/actions are useful validation material but are not automatically reasoning trajectories.

## Oracle boundary

Frontier models or humans may create concise external annotations such as `observation`, `candidate hypothesis`, `prediction`, `evidence checked`, `counterexample`, and `revision`. They may not provide hidden reasoning-token access, test targets to the live agent, or task-specific answer dispatch.
