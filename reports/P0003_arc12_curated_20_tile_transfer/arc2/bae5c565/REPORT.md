# ARC2 `bae5c565` IHL Brain Surgery Report

## Outcome: NO — TEST CELLS DO NOT ALL MATCH

- **Compared positions:** 121
- **Mismatched cells:** 40
- **Source commit:** `71f86ff4c5304e452e0659131171f0519b50e21c`
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
- **Mismatched cells:** `40`
- **Prediction:**
```json
[[4, 6, 7, 2, 9, 5, 3, 3, 4, 3, 3], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 5]]
```
- **Expected output (post-answer only):**
```json
[[5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 5], [5, 5, 5, 5, 9, 8, 3, 5, 5, 5, 5], [5, 5, 5, 2, 9, 8, 3, 3, 5, 5, 5], [5, 5, 7, 2, 9, 8, 3, 3, 4, 5, 5], [5, 6, 7, 2, 9, 8, 3, 3, 4, 3, 5], [4, 6, 7, 2, 9, 8, 3, 3, 4, 3, 3]]
```

## Observable IHL Walkthrough

The record contains explicit actions, predictions, feedback, and revisions; it does not claim or store hidden model reasoning.

### Action totals

- `APPLY_HYPOTHESIS`: 64
- `ATTEND`: 1
- `COMMIT`: 1
- `COMPARE`: 64
- `FIND_COUNTEREXAMPLE`: 64
- `PROPOSE`: 2
- `REJECT_HYPOTHESIS`: 64
- `SPECIALIZE`: 1

### Decision milestones

- `0` `ATTEND` — `{"demo_change_counts":[{"changed_cells":66,"demo_index":0},{"changed_cells":36,"demo_index":1}],"evidence_world_count":2,"selected_demo":0}`
- `1` `PROPOSE` — `{"generic_candidate_count":628,"locally_ranked_candidate_count":32,"stage":"global_generic_relations"}`
- `130` `SPECIALIZE` — `{"next_operator_family":"generic_line_and_span_relations","reason":"no_global_training_complete_hypothesis","retained_partial_hypothesis_count":0}`
- `131` `PROPOSE` — `{"generic_candidate_count":360,"locally_ranked_candidate_count":32,"stage":"residual_directed_generic_relations"}`
- `260` `COMMIT` — `{"complete_prediction_group_count":0,"fallback_reason":"no_complete_training_compatible_generic_hypothesis","posterior_mass":0.0,"selected_hypothesis":"fallback_identity_complete_grid","training_exact":false}`

### First counterexamples

- `4` — `{"counterexample":{"column":6,"demo_index":0,"observed":8,"predicted":5,"row":5},"hypothesis":"translate(column_offset=0,row_offset=12)","stage":"global_generic_relations"}`
- `8` — `{"counterexample":{"column":6,"demo_index":0,"observed":8,"predicted":5,"row":5},"hypothesis":"translate(column_offset=0,row_offset=11)","stage":"global_generic_relations"}`
- `12` — `{"counterexample":{"column":6,"demo_index":0,"observed":5,"predicted":8,"row":0},"hypothesis":"mirror(axis=top_bottom)","stage":"global_generic_relations"}`
- `16` — `{"counterexample":{"column":6,"demo_index":0,"observed":8,"predicted":5,"row":5},"hypothesis":"translate(column_offset=0,row_offset=10)","stage":"global_generic_relations"}`
- `20` — `{"counterexample":{"column":6,"demo_index":0,"observed":5,"predicted":8,"row":4},"hypothesis":"translate(column_offset=0,row_offset=-1)","stage":"global_generic_relations"}`
- `59` additional explicit counterexamples are retained in `learning_trace.json`.
