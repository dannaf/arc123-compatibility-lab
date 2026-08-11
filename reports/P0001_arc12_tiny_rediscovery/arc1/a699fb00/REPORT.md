# ARC1 `a699fb00` IHL Brain Surgery Report

## Outcome: YES — ALL TEST CELLS MATCH

- **Compared positions:** 100
- **Mismatched cells:** 0
- **Source commit:** `085f6dbe39050afac3d1d743f840bac95b1a8d1c`
- **Selected hypothesis:** `row_span_fill(fill_color=2,seed_color=1)`
- **Training compatibility:** `True`
- **Fallback used:** `False`

## Live-Agent Boundary

The controller receives only training input/output evidence and the test input. It receives no task ID, historical schema/decomposition, GT feature contract, GT solver, or test target. The expected test output below is accessed only after the complete prediction is committed for V&V.

## Corpus-Callosum Visualization

![ARC123 corpus-callosum trace](corpus_callosum.svg)

- Full explicit event record: [`learning_trace.json`](learning_trace.json)

The diagram shows the actual test input, the typed compatibility core, and the committed full prediction. It renders observable operations only; it does not fabricate a one-to-one causal fiber where the selected program is only a factor-level dependency.

## Post-Answer V&V

### Test case 1
- **All cells match:** `True`
- **Mismatched cells:** `0`
- **Prediction:**
```json
[[0, 1, 2, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 2, 1, 2, 1, 2, 1, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 2, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 2, 1, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 2, 1, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
```
- **Expected output (post-answer only):**
```json
[[0, 1, 2, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 2, 1, 2, 1, 2, 1, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 2, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 2, 1, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 2, 1, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
```

## Observable IHL Walkthrough

The record contains explicit actions, predictions, feedback, and revisions; it does not claim or store hidden model reasoning.

### Action totals

- `APPLY_HYPOTHESIS`: 62
- `ATTEND`: 1
- `COMMIT`: 1
- `COMPARE`: 62
- `FIND_COUNTEREXAMPLE`: 61
- `PROMOTE_CONSTRAINT`: 1
- `PROPOSE`: 2
- `REJECT_HYPOTHESIS`: 61
- `SPECIALIZE`: 1

### Decision milestones

- `0` `ATTEND` — `{"demo_change_counts":[{"changed_cells":6,"demo_index":1},{"changed_cells":6,"demo_index":2},{"changed_cells":2,"demo_index":0}],"evidence_world_count":3,"selected_demo":1}`
- `1` `PROPOSE` — `{"generic_candidate_count":364,"locally_ranked_candidate_count":32,"stage":"global_generic_relations"}`
- `130` `SPECIALIZE` — `{"next_operator_family":"generic_line_and_span_relations","reason":"no_global_training_complete_hypothesis","retained_partial_hypothesis_count":0}`
- `131` `PROPOSE` — `{"generic_candidate_count":30,"locally_ranked_candidate_count":30,"stage":"residual_directed_generic_relations"}`
- `134` `PROMOTE_CONSTRAINT` — `{"hypothesis":"row_span_fill(fill_color=2,seed_color=1)","stage":"residual_directed_generic_relations","status":"full_training_compatibility"}`
- `251` `COMMIT` — `{"complete_prediction_group_count":1,"posterior_mass":1.0,"selected_hypothesis":"row_span_fill(fill_color=2,seed_color=1)","training_exact":true}`

### First counterexamples

- `4` — `{"counterexample":{"column":1,"demo_index":0,"observed":2,"predicted":0,"row":0},"hypothesis":"identity","stage":"global_generic_relations"}`
- `8` — `{"counterexample":{"column":0,"demo_index":0,"observed":1,"predicted":0,"row":0},"hypothesis":"mirror(axis=left_right)","stage":"global_generic_relations"}`
- `12` — `{"counterexample":{"column":0,"demo_index":0,"observed":1,"predicted":0,"row":0},"hypothesis":"translate(column_offset=1,row_offset=3)","stage":"global_generic_relations"}`
- `16` — `{"counterexample":{"column":1,"demo_index":0,"observed":2,"predicted":0,"row":0},"hypothesis":"translate(column_offset=-2,row_offset=0)","stage":"global_generic_relations"}`
- `20` — `{"counterexample":{"column":1,"demo_index":0,"observed":2,"predicted":0,"row":0},"hypothesis":"translate(column_offset=-1,row_offset=-3)","stage":"global_generic_relations"}`
- `56` additional explicit counterexamples are retained in `learning_trace.json`.
