# ARC1 `833dafe3` IHL Brain Surgery Report

## Outcome: NO — TEST CELLS DO NOT ALL MATCH

- **Compared positions:** 256
- **Mismatched cells:** 256
- **Source commit:** `085f6dbe39050afac3d1d743f840bac95b1a8d1c`
- **Selected hypothesis:** `fallback_identity_complete_grid`
- **Training compatibility:** `False`
- **Fallback used:** `True`

## Live-Agent Boundary

The controller receives only training input/output evidence and the test input. It receives no task ID, historical schema/decomposition, GT feature contract, GT solver, or test target. The expected test output below is accessed only after the complete prediction is committed for V&V.

## Corpus-Callosum Visualization

![ARC123 corpus-callosum trace](corpus_callosum.svg)

- Full explicit event record: [`learning_trace.json`](learning_trace.json)

The diagram shows the actual test input, the typed compatibility core, and the committed full prediction. It renders observable operations only; it does not fabricate a one-to-one causal fiber where the selected program is only a factor-level dependency.

## Post-Answer V&V

### Test case 1
- **All cells match:** `False`
- **Mismatched cells:** `256`
- **Prediction:**
```json
[[0, 0, 1, 0, 0, 0, 0, 0], [0, 2, 1, 0, 9, 0, 0, 0], [0, 2, 1, 0, 9, 0, 0, 0], [0, 2, 1, 0, 9, 1, 1, 1], [9, 2, 0, 0, 9, 0, 0, 0], [9, 2, 0, 0, 9, 0, 0, 9], [1, 2, 0, 0, 9, 0, 0, 9], [9, 9, 0, 0, 9, 0, 0, 9]]
```
- **Expected output (post-answer only):**
```json
[[9, 0, 0, 9, 0, 0, 9, 9, 9, 9, 0, 0, 9, 0, 0, 9], [9, 0, 0, 9, 0, 0, 2, 1, 1, 2, 0, 0, 9, 0, 0, 9], [9, 0, 0, 9, 0, 0, 2, 9, 9, 2, 0, 0, 9, 0, 0, 9], [0, 0, 0, 9, 0, 0, 2, 9, 9, 2, 0, 0, 9, 0, 0, 0], [1, 1, 1, 9, 0, 1, 2, 0, 0, 2, 1, 0, 9, 1, 1, 1], [0, 0, 0, 9, 0, 1, 2, 0, 0, 2, 1, 0, 9, 0, 0, 0], [0, 0, 0, 9, 0, 1, 2, 0, 0, 2, 1, 0, 9, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 9, 0, 1, 2, 0, 0, 2, 1, 0, 9, 0, 0, 0], [0, 0, 0, 9, 0, 1, 2, 0, 0, 2, 1, 0, 9, 0, 0, 0], [1, 1, 1, 9, 0, 1, 2, 0, 0, 2, 1, 0, 9, 1, 1, 1], [0, 0, 0, 9, 0, 0, 2, 9, 9, 2, 0, 0, 9, 0, 0, 0], [9, 0, 0, 9, 0, 0, 2, 9, 9, 2, 0, 0, 9, 0, 0, 9], [9, 0, 0, 9, 0, 0, 2, 1, 1, 2, 0, 0, 9, 0, 0, 9], [9, 0, 0, 9, 0, 0, 9, 9, 9, 9, 0, 0, 9, 0, 0, 9]]
```

## Observable IHL Walkthrough

The record contains explicit actions, predictions, feedback, and revisions; it does not claim or store hidden model reasoning.

### Action totals

- `APPLY_HYPOTHESIS`: 2
- `ATTEND`: 1
- `COMMIT`: 1
- `COMPARE`: 2
- `FIND_COUNTEREXAMPLE`: 1
- `PROPOSE`: 2
- `REJECT_HYPOTHESIS`: 2
- `SPECIALIZE`: 1

### Decision milestones

- `0` `ATTEND` — `{"demo_change_counts":[{"changed_cells":64,"demo_index":1},{"changed_cells":36,"demo_index":0}],"evidence_world_count":2,"selected_demo":1}`
- `1` `PROPOSE` — `{"generic_candidate_count":2,"locally_ranked_candidate_count":2,"stage":"global_generic_relations"}`
- `9` `SPECIALIZE` — `{"next_operator_family":"generic_line_and_span_relations","reason":"no_global_training_complete_hypothesis","retained_partial_hypothesis_count":0}`
- `10` `PROPOSE` — `{"generic_candidate_count":0,"locally_ranked_candidate_count":0,"stage":"residual_directed_generic_relations"}`
- `11` `COMMIT` — `{"complete_prediction_group_count":0,"fallback_reason":"no_complete_training_compatible_generic_hypothesis","posterior_mass":0.0,"selected_hypothesis":"fallback_identity_complete_grid","training_exact":false}`

### First counterexamples

- `7` — `{"counterexample":{"column":0,"demo_index":0,"observed":2,"predicted":3,"row":0},"hypothesis":"tile_repeat(column_factor=2,row_factor=2)","stage":"global_generic_relations"}`
