# ARC1 `2281f1f4` IHL Brain Surgery Report

## Outcome: NO — TEST CELLS DO NOT ALL MATCH

- **Compared positions:** 100
- **Mismatched cells:** 25
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
- **Mismatched cells:** `25`
- **Prediction:**
```json
[[5, 0, 5, 5, 0, 0, 5, 0, 5, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 5], [0, 0, 0, 0, 0, 0, 0, 0, 0, 5], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 5], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 5], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 5]]
```
- **Expected output (post-answer only):**
```json
[[5, 0, 5, 5, 0, 0, 5, 0, 5, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [2, 0, 2, 2, 0, 0, 2, 0, 2, 5], [2, 0, 2, 2, 0, 0, 2, 0, 2, 5], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [2, 0, 2, 2, 0, 0, 2, 0, 2, 5], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [2, 0, 2, 2, 0, 0, 2, 0, 2, 5], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [2, 0, 2, 2, 0, 0, 2, 0, 2, 5]]
```

## Observable IHL Walkthrough

The record contains explicit actions, predictions, feedback, and revisions; it does not claim or store hidden model reasoning.

### Action totals

- `APPLY_HYPOTHESIS`: 62
- `ATTEND`: 1
- `COMMIT`: 1
- `COMPARE`: 62
- `FIND_COUNTEREXAMPLE`: 62
- `PROPOSE`: 2
- `REJECT_HYPOTHESIS`: 62
- `SPECIALIZE`: 1

### Decision milestones

- `0` `ATTEND` — `{"demo_change_counts":[{"changed_cells":20,"demo_index":2},{"changed_cells":12,"demo_index":1},{"changed_cells":6,"demo_index":0}],"evidence_world_count":3,"selected_demo":2}`
- `1` `PROPOSE` — `{"generic_candidate_count":364,"locally_ranked_candidate_count":32,"stage":"global_generic_relations"}`
- `130` `SPECIALIZE` — `{"next_operator_family":"generic_line_and_span_relations","reason":"no_global_training_complete_hypothesis","retained_partial_hypothesis_count":0}`
- `131` `PROPOSE` — `{"generic_candidate_count":30,"locally_ranked_candidate_count":30,"stage":"residual_directed_generic_relations"}`
- `252` `COMMIT` — `{"complete_prediction_group_count":0,"fallback_reason":"no_complete_training_compatible_generic_hypothesis","posterior_mass":0.0,"selected_hypothesis":"fallback_identity_complete_grid","training_exact":false}`

### First counterexamples

- `4` — `{"counterexample":{"column":0,"demo_index":0,"observed":2,"predicted":0,"row":3},"hypothesis":"identity","stage":"global_generic_relations"}`
- `8` — `{"counterexample":{"column":0,"demo_index":0,"observed":5,"predicted":0,"row":0},"hypothesis":"translate(column_offset=9,row_offset=7)","stage":"global_generic_relations"}`
- `12` — `{"counterexample":{"column":0,"demo_index":0,"observed":5,"predicted":0,"row":0},"hypothesis":"translate(column_offset=9,row_offset=3)","stage":"global_generic_relations"}`
- `16` — `{"counterexample":{"column":0,"demo_index":0,"observed":5,"predicted":0,"row":0},"hypothesis":"translate(column_offset=7,row_offset=0)","stage":"global_generic_relations"}`
- `20` — `{"counterexample":{"column":0,"demo_index":0,"observed":5,"predicted":0,"row":0},"hypothesis":"translate(column_offset=0,row_offset=-4)","stage":"global_generic_relations"}`
- `57` additional explicit counterexamples are retained in `learning_trace.json`.
