# ARC2 `15660dd6` P0015-ARC12-AXIS-MODE-DENOISE-DEVELOPMENT-40 Brain Surgery Report

## Outcome: NO — TEST CELLS DO NOT ALL MATCH

- **Compared positions:** 161
- **Mismatched cells:** 161
- **Training compatibility:** `False`
- **Fallback used:** `True`
- **Selected hypothesis:** `fallback_identity_complete_grid`
- **Source commit:** `71f86ff4c5304e452e0659131171f0519b50e21c`
- **Frozen controller commit:** `9a1e9e8f87fb08ca3b13e9dc9c6a7cfdfdb379ae`

## Live-Agent Boundary

The controller receives only visible training input/output examples and test inputs. It receives no task ID, imported cohort metadata, GT feature contract, GT solver, historical decomposition, or held-out output before committing a complete grid. The expected output appears only in post-answer V&V.

## Corpus-Callosum Visualization

![corpus-callosum trace](corpus_callosum.svg)

- Full explicit event record: [`learning_trace.json`](learning_trace.json)

## Frozen Measurement

The controller bytes, generic operator vocabulary, source task checksums, and cohort membership were frozen before this task was parsed or scored. This result cannot tune the frozen controller.

## Post-Answer V&V

### Test case 1
- **All cells match:** `False`
- **Mismatched cells:** `161`
- **Prediction:**
```json
[[8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8], [5, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8], [5, 1, 8, 8, 2, 8, 8, 1, 8, 1, 8, 2, 8, 8, 8, 1, 8, 1, 3, 3, 3, 3, 3, 1, 8], [5, 1, 8, 2, 2, 2, 8, 1, 8, 1, 2, 2, 2, 2, 8, 1, 8, 1, 3, 3, 3, 3, 3, 1, 8], [5, 1, 8, 8, 2, 8, 8, 1, 8, 1, 8, 8, 8, 2, 8, 1, 8, 1, 3, 3, 3, 3, 3, 1, 8], [5, 1, 2, 2, 2, 2, 2, 1, 8, 1, 8, 2, 2, 2, 2, 1, 8, 1, 3, 3, 3, 3, 3, 1, 8], [5, 1, 8, 8, 2, 8, 8, 1, 8, 1, 8, 8, 8, 2, 8, 1, 8, 1, 3, 3, 3, 3, 3, 1, 8], [5, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8], [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8], [9, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8], [9, 1, 6, 6, 6, 6, 6, 1, 8, 1, 8, 2, 8, 8, 8, 1, 8, 1, 8, 8, 8, 2, 2, 1, 8], [9, 1, 6, 6, 6, 6, 6, 1, 8, 1, 2, 2, 2, 2, 8, 1, 8, 1, 8, 8, 8, 2, 2, 1, 8], [9, 1, 6, 6, 6, 6, 6, 1, 8, 1, 8, 8, 8, 2, 8, 1, 8, 1, 8, 2, 2, 8, 8, 1, 8], [9, 1, 6, 6, 6, 6, 6, 1, 8, 1, 8, 2, 2, 2, 2, 1, 8, 1, 2, 2, 2, 8, 8, 1, 8], [9, 1, 6, 6, 6, 6, 6, 1, 8, 1, 8, 8, 8, 2, 8, 1, 8, 1, 8, 2, 8, 8, 8, 1, 8], [9, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8], [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8], [0, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8], [0, 1, 8, 8, 2, 8, 8, 1, 8, 1, 4, 4, 4, 4, 4, 1, 8, 1, 8, 8, 8, 2, 2, 1, 8], [0, 1, 8, 2, 2, 2, 8, 1, 8, 1, 4, 4, 4, 4, 4, 1, 8, 1, 8, 8, 8, 2, 2, 1, 8], [0, 1, 8, 8, 2, 8, 8, 1, 8, 1, 4, 4, 4, 4, 4, 1, 8, 1, 8, 2, 2, 8, 8, 1, 8], [0, 1, 2, 2, 2, 2, 2, 1, 8, 1, 4, 4, 4, 4, 4, 1, 8, 1, 2, 2, 2, 8, 8, 1, 8], [0, 1, 8, 8, 2, 8, 8, 1, 8, 1, 4, 4, 4, 4, 4, 1, 8, 1, 8, 2, 8, 8, 8, 1, 8], [0, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 8], [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8]]
```
- **Expected output (post-answer only):**
```json
[[9, 9, 9, 9, 9, 9, 9, 8, 0, 0, 0, 0, 0, 0, 0, 8, 5, 5, 5, 5, 5, 5, 5], [9, 8, 8, 6, 8, 8, 9, 8, 0, 8, 4, 8, 8, 8, 0, 8, 5, 8, 8, 8, 3, 3, 5], [9, 8, 6, 6, 6, 8, 9, 8, 0, 4, 4, 4, 4, 8, 0, 8, 5, 8, 8, 8, 3, 3, 5], [9, 8, 8, 6, 8, 8, 9, 8, 0, 8, 8, 8, 4, 8, 0, 8, 5, 8, 3, 3, 8, 8, 5], [9, 6, 6, 6, 6, 6, 9, 8, 0, 8, 4, 4, 4, 4, 0, 8, 5, 3, 3, 3, 8, 8, 5], [9, 8, 8, 6, 8, 8, 9, 8, 0, 8, 8, 8, 4, 8, 0, 8, 5, 8, 3, 8, 8, 8, 5], [9, 9, 9, 9, 9, 9, 9, 8, 0, 0, 0, 0, 0, 0, 0, 8, 5, 5, 5, 5, 5, 5, 5]]
```

## Observable IHL Walkthrough

The record contains explicit actions, predictions, feedback, and revisions; it does not claim or store hidden model reasoning.

### Action totals

- `APPLY_HYPOTHESIS`: 8
- `ATTEND`: 8
- `CHOOSE_NEXT_DEMO`: 8
- `COMMIT`: 1
- `COMPARE`: 8
- `PROPOSE`: 4
- `REJECT_RULE`: 4

### Decision milestones

- `0` `PROPOSE` — `{"parent_theory_id":"T0000","rule":{"description_length":1,"name":"identity","operation":"identity","parameters":{},"rule_id":"identity","scope":{"kind":"all","value":null}},"stage":"initial_generic_theories","theory_id":"T0001"}`
- `1` `PROPOSE` — `{"parent_theory_id":"T0000","rule":{"description_length":2,"name":"left_right(scope=all)","operation":"coordinate_transform","parameters":{"axis":"left_right"},"rule_id":"coordinate-left_right","scope":{"kind":"all","value":null}},"stage":"initial_generic_theories","theory_id":"T0002"}`
- `2` `PROPOSE` — `{"parent_theory_id":"T0000","rule":{"description_length":2,"name":"top_bottom(scope=all)","operation":"coordinate_transform","parameters":{"axis":"top_bottom"},"rule_id":"coordinate-top_bottom","scope":{"kind":"all","value":null}},"stage":"initial_generic_theories","theory_id":"T0003"}`
- `3` `PROPOSE` — `{"parent_theory_id":"T0000","rule":{"description_length":2,"name":"rotate_180(scope=all)","operation":"coordinate_transform","parameters":{"axis":"rotate_180"},"rule_id":"coordinate-rotate_180","scope":{"kind":"all","value":null}},"stage":"initial_generic_theories","theory_id":"T0004"}`
- `5` `ATTEND` — `{"reason":"initial_highest_observed_change_and_color_discrimination","selected_demo":1,"selected_region":{"region":"whole_demo"},"theory_id":"T0001"}`
- `9` `ATTEND` — `{"reason":"initial_highest_observed_change_and_color_discrimination","selected_demo":1,"selected_region":{"region":"whole_demo"},"theory_id":"T0002"}`
- `13` `ATTEND` — `{"reason":"initial_highest_observed_change_and_color_discrimination","selected_demo":1,"selected_region":{"region":"whole_demo"},"theory_id":"T0003"}`
- `17` `ATTEND` — `{"reason":"initial_highest_observed_change_and_color_discrimination","selected_demo":1,"selected_region":{"region":"whole_demo"},"theory_id":"T0004"}`
- `21` `ATTEND` — `{"reason":"unseen_demo_selected_for_residual_version_space_discrimination","selected_demo":0,"selected_region":{"region":"whole_demo"},"theory_id":"T0001"}`
- `25` `ATTEND` — `{"reason":"unseen_demo_selected_for_residual_version_space_discrimination","selected_demo":0,"selected_region":{"region":"whole_demo"},"theory_id":"T0002"}`
- `29` `ATTEND` — `{"reason":"unseen_demo_selected_for_residual_version_space_discrimination","selected_demo":0,"selected_region":{"region":"whole_demo"},"theory_id":"T0003"}`
- `33` `ATTEND` — `{"reason":"unseen_demo_selected_for_residual_version_space_discrimination","selected_demo":0,"selected_region":{"region":"whole_demo"},"theory_id":"T0004"}`
- `40` `COMMIT` — `{"best_partial_theory":{"contradiction_count":0,"counterexamples":[],"description_length":1,"evaluated_demo_indices":[],"history":[{"kind":"ADD_RULE","parameters":{"initial_proposal":true,"operation":"identity"},"target":"identity"}],"matching_cell_count":0,"name":"identity","parameter_bindings":{},"parent_theory_id":"T0000","rules":[{"description_length":1,"name":"identity","operation":"identity","parameters":{},"rule_id":"identity","scope":{"kind":"all","value":null}}],"scope_predicates":[{"kind":"all","value":null}],"theory_id":"T0001","unknown_cell_count":0,"unresolved_unknown":[]},"complete_prediction_group_count":0,"fallback_reason":"no_complete_training_compatible_partial_theory","posterior_mass":0.0,"selected_hypothesis":"fallback_identity_complete_grid","training_exact":false}`
