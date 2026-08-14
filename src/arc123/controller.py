"""A deterministic non-VLM controller for iterative hypothesis learning."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from .arc3_mechanics import (
    GoalDirectedAction,
    choose_goal_directed_action,
    learn_motion_model,
    observed_controlled_delta,
)
from .compatibility import assess_hypothesis
from .contracts import EnvironmentAction, HypothesisAction, ObservationWorld, TransitionFeedback
from .hypotheses import Hypothesis, propose_base_hypotheses, propose_structural_hypotheses
from .model import ActionKind, Grid, HypothesisAssessment, PartialGrid, SolveResult, TrainingPair
from .perceptions import background_color, difference_summary
from .relational import (
    deserialize_mapping,
    infer_component_property_erase_specs,
    infer_component_property_recolor_specs,
    infer_marker_shape_target_recolor_specs,
)
from .theory import (
    PartialTheory,
    ScopePredicate,
    TheoryRule,
    coordinate_transform_rule,
    evaluate_theory_demo,
    recolor_scoped_rule,
)
from .traces import LearningTrace


class EvidenceEnvironment(Protocol):
    training_pairs: tuple[TrainingPair, ...]
    test_inputs: tuple[Grid, ...]


class Predictor(Protocol):
    name: str
    description_length: int

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]: ...


DEFAULT_OPERATOR_FAMILIES = (
    "identity",
    "recolor",
    "mirror",
    "dihedral_transform",
    "translate",
    "frame_interior_crop",
    "central_separator_cellwise_combine",
    "adjacent_bilateral_cellwise_combine",
    "distinct_nonbackground_scale",
    "distinct_color_scale",
    "quadrant_odd_one_out",
    "cross_separator_quadrant_reflection_stamp",
    "repeated_panel_odd_one_out_crop",
    "singleton_foreground_border",
    "distinct_color_count_line",
    "separated_panel_cellwise_combine",
    "contiguous_panel_cellwise_combine",
    "unique_component_crop",
    "anti_diagonal_nonbackground_stream",
    "symmetric_foreground_quadrant_crop",
    "uniform_block_self_stamp_fractal",
    "line_extend",
    "row_span_fill",
    "partial-with-identity composition",
)


@dataclass(frozen=True)
class _CompletedPartialHypothesis:
    """Generic composition of a partial theory with identity over its UNKNOWN cells."""

    partial: Predictor

    @property
    def name(self) -> str:
        return f"compose(identity,{self.partial.name})"

    @property
    def description_length(self) -> int:
        return self.partial.description_length + 1

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        prediction = self.partial.predict(input_grid)
        if prediction is None or len(prediction) != len(input_grid) or any(
            len(predicted_row) != len(input_row)
            for predicted_row, input_row in zip(prediction, input_grid)
        ):
            return None
        return tuple(
            tuple(
                predicted if predicted is not None else input_color
                for predicted, input_color in zip(predicted_row, input_row)
            )
            for predicted_row, input_row in zip(prediction, input_grid)
        )


def _rank_key(assessment: HypothesisAssessment) -> tuple[int, int, int, int, int, str]:
    return (
        int(assessment.contradiction_count == 0),
        assessment.matching_cell_count,
        assessment.asserted_cell_count,
        -assessment.contradiction_count,
        -assessment.description_length,
        assessment.hypothesis_name,
    )


def _complete_prediction(predictor: Predictor, input_grid: Grid) -> Optional[Grid]:
    prediction = predictor.predict(input_grid)
    if prediction is None or any(cell is None for row in prediction for cell in row):
        return None
    return tuple(tuple(int(cell) for cell in row) for row in prediction)


class StagedCandidateBaseline:
    """Searches visible hypothesis operations rather than dispatching task schemas."""

    def __init__(
        self,
        candidate_limit: int = 32,
        operator_families: Sequence[str] | None = None,
    ) -> None:
        if candidate_limit < 1:
            raise ValueError("candidate_limit must be positive")
        self.candidate_limit = candidate_limit
        self.operator_families = tuple(
            DEFAULT_OPERATOR_FAMILIES if operator_families is None else operator_families
        )

    def _rank_candidates(
        self, candidates: Sequence[Predictor], training_pairs: Sequence[TrainingPair]
    ) -> list[Predictor]:
        attended_pair = (training_pairs[0],)
        scored = [
            (candidate, assess_hypothesis(candidate, attended_pair))
            for candidate in candidates
        ]
        scored.sort(key=lambda item: _rank_key(item[1]), reverse=True)
        return [candidate for candidate, _ in scored[: self.candidate_limit]]

    def _evaluate_stage(
        self,
        stage: str,
        candidates: Sequence[Predictor],
        training_pairs: Sequence[TrainingPair],
        trace: LearningTrace,
        exact: list[tuple[Predictor, HypothesisAssessment]],
        partial: list[tuple[Predictor, HypothesisAssessment]],
    ) -> None:
        retained = self._rank_candidates(candidates, training_pairs)
        trace.record(
            ActionKind.PROPOSE,
            stage=stage,
            generic_candidate_count=len(candidates),
            locally_ranked_candidate_count=len(retained),
        )
        for candidate in retained:
            assessment = assess_hypothesis(candidate, training_pairs)
            trace.record(
                ActionKind.APPLY_HYPOTHESIS,
                stage=stage,
                hypothesis=candidate.name,
                description_length=candidate.description_length,
            )
            trace.record(ActionKind.COMPARE, stage=stage, **assessment.as_dict())
            if assessment.is_training_exact:
                exact.append((candidate, assessment))
                trace.record(
                    ActionKind.PROMOTE_CONSTRAINT,
                    stage=stage,
                    hypothesis=candidate.name,
                    status="full_training_compatibility",
                )
                continue
            counterexample = assessment.first_counterexample
            if counterexample is not None:
                trace.record(
                    ActionKind.FIND_COUNTEREXAMPLE,
                    stage=stage,
                    hypothesis=candidate.name,
                    counterexample=counterexample.as_dict(),
                )
                trace.record(
                    ActionKind.REJECT_HYPOTHESIS,
                    stage=stage,
                    hypothesis=candidate.name,
                    reason="observed_contradiction_exact_support_zero",
                )
                continue
            if assessment.is_partial_compatible:
                partial.append((candidate, assessment))
                trace.record(
                    ActionKind.PROMOTE_CONSTRAINT,
                    stage=stage,
                    hypothesis=candidate.name,
                    status="partial_compatible_unknown_cells_retained",
                    unknown_cell_count=assessment.unknown_cell_count,
                )
                continue
            trace.record(
                ActionKind.REJECT_HYPOTHESIS,
                stage=stage,
                hypothesis=candidate.name,
                reason="no_observed_explanatory_coverage",
            )

    def _collapse(
        self,
        exact: Sequence[tuple[Predictor, HypothesisAssessment]],
        test_inputs: Sequence[Grid],
        trace: LearningTrace,
    ) -> Optional[tuple[tuple[Grid, ...], str, float]]:
        groups: dict[str, list[tuple[Predictor, HypothesisAssessment, tuple[Grid, ...]]]] = {}
        for candidate, assessment in exact:
            predictions = tuple(
                prediction
                for input_grid in test_inputs
                if (prediction := _complete_prediction(candidate, input_grid)) is not None
            )
            if len(predictions) != len(test_inputs):
                trace.record(
                    ActionKind.REJECT_HYPOTHESIS,
                    hypothesis=candidate.name,
                    reason="test_prediction_remains_unknown",
                )
                continue
            key = json.dumps(predictions)
            groups.setdefault(key, []).append((candidate, assessment, predictions))
        if not groups:
            return None
        unnormalized = {
            key: sum(math.exp(-assessment.description_length) for _, assessment, _ in entries)
            for key, entries in groups.items()
        }
        total_mass = sum(unnormalized.values())
        chosen_key, chosen_mass = max(
            unnormalized.items(), key=lambda item: (item[1], item[0])
        )
        chosen_entries = groups[chosen_key]
        chosen_predictor, _, chosen_predictions = min(
            chosen_entries,
            key=lambda item: (item[1].description_length, item[0].name),
        )
        if len(chosen_entries) > 1:
            trace.record(
                ActionKind.MERGE_RULES,
                compatible_hypotheses=[item[0].name for item in chosen_entries],
                complete_prediction_group_size=len(chosen_entries),
            )
        posterior_mass = chosen_mass / total_mass
        trace.record(
            ActionKind.COMMIT,
            selected_hypothesis=chosen_predictor.name,
            complete_prediction_group_count=len(groups),
            posterior_mass=posterior_mass,
            training_exact=True,
        )
        return chosen_predictions, chosen_predictor.name, posterior_mass

    def solve(self, environment: EvidenceEnvironment, episode_id: str = "arc12-task") -> SolveResult:
        """Return a complete answer using only training demonstrations and test inputs."""

        training_pairs = environment.training_pairs
        trace = LearningTrace(episode_id)
        attended_demos = sorted(
            (
                (index, difference_summary(input_grid, output_grid)["changed_cell_count"])
                for index, (input_grid, output_grid) in enumerate(training_pairs)
            ),
            key=lambda item: (-int(item[1]), item[0]),
        )
        trace.record(
            ActionKind.ATTEND,
            selected_demo=attended_demos[0][0],
            demo_change_counts=[{"demo_index": index, "changed_cells": count} for index, count in attended_demos],
            evidence_world_count=len(training_pairs),
        )
        exact: list[tuple[Predictor, HypothesisAssessment]] = []
        partial: list[tuple[Predictor, HypothesisAssessment]] = []
        self._evaluate_stage(
            "global_generic_relations",
            propose_base_hypotheses(training_pairs, self.operator_families),
            training_pairs,
            trace,
            exact,
            partial,
        )
        if not exact:
            trace.record(
                ActionKind.SPECIALIZE,
                reason="no_global_training_complete_hypothesis",
                retained_partial_hypothesis_count=len(partial),
                next_operator_family="generic_line_and_span_relations",
            )
            self._evaluate_stage(
                "residual_directed_generic_relations",
                propose_structural_hypotheses(training_pairs, self.operator_families),
                training_pairs,
                trace,
                exact,
                partial,
            )
        if (
            not exact
            and partial
            and "partial-with-identity composition" in self.operator_families
        ):
            partial_candidate, partial_assessment = min(
                partial,
                key=lambda item: (-item[1].matching_cell_count, item[0].description_length, item[0].name),
            )
            composite = _CompletedPartialHypothesis(partial_candidate)
            trace.record(
                ActionKind.COMPOSE,
                base="identity",
                partial_hypothesis=partial_candidate.name,
                unknown_cell_count=partial_assessment.unknown_cell_count,
            )
            composite_assessment = assess_hypothesis(composite, training_pairs)
            trace.record(ActionKind.COMPARE, stage="composition", **composite_assessment.as_dict())
            if composite_assessment.is_training_exact:
                exact.append((composite, composite_assessment))
                trace.record(
                    ActionKind.PROMOTE_CONSTRAINT,
                    stage="composition",
                    hypothesis=composite.name,
                    status="full_training_compatibility",
                )
        collapsed = self._collapse(exact, environment.test_inputs, trace)
        if collapsed is not None:
            predictions, selected_hypothesis, posterior_mass = collapsed
            return SolveResult(
                predictions=predictions,
                selected_hypothesis=selected_hypothesis,
                training_exact=True,
                used_fallback=False,
                posterior_mass=posterior_mass,
                trace=trace.as_dict(),
            )
        predictions = tuple(tuple(tuple(row) for row in input_grid) for input_grid in environment.test_inputs)
        trace.record(
            ActionKind.COMMIT,
            selected_hypothesis="fallback_identity_complete_grid",
            complete_prediction_group_count=0,
            posterior_mass=0.0,
            training_exact=False,
            fallback_reason="no_complete_training_compatible_generic_hypothesis",
        )
        return SolveResult(
            predictions=predictions,
            selected_hypothesis="fallback_identity_complete_grid",
            training_exact=False,
            used_fallback=True,
            posterior_mass=0.0,
            trace=trace.as_dict(),
        )


THEORY_OPERATOR_FAMILIES = (
    "identity",
    "recolor",
    "mirror",
    "translate",
    "repeat_tile",
    "dihedral_tile",
    "self_mask_macro_stamp",
    "axis_mode_denoise",
    "self_contained_subset_crop",
    "frame_interior_crop",
    "central_separator_cellwise_combine",
    "adjacent_bilateral_cellwise_combine",
    "distinct_nonbackground_scale",
    "distinct_color_scale",
    "quadrant_odd_one_out",
    "cross_separator_quadrant_reflection_stamp",
    "repeated_panel_odd_one_out_crop",
    "singleton_foreground_border",
    "distinct_color_count_line",
    "separated_panel_cellwise_combine",
    "contiguous_panel_cellwise_combine",
    "unique_component_crop",
    "anti_diagonal_nonbackground_stream",
    "symmetric_foreground_quadrant_crop",
    "uniform_block_self_stamp_fractal",
    "line_extend",
    "row_span_fill",
    "row_span_minimum",
    "scoped_coordinate_transform",
    "component_property_recolor",
    "component_property_erase",
    "marker_shape_target_recolor",
)


class IterativeHypothesisLearner:
    """Bounded best-first revision over persistent partial theories.

    This controller intentionally keeps a theory after a contradiction whenever a
    counterexample can target one rule or scope. It does not load task IDs, held-out
    outputs, ARC12 decompositions, GT features, or solver code.
    """

    def __init__(
        self,
        candidate_limit: int = 32,
        operator_families: Sequence[str] | None = None,
        beam_width: int | None = None,
        max_revisions: int = 96,
        revision_enabled: bool = True,
    ) -> None:
        if candidate_limit < 1:
            raise ValueError("candidate_limit must be positive")
        if max_revisions < 1:
            raise ValueError("max_revisions must be positive")
        self.candidate_limit = candidate_limit
        self.operator_families = tuple(
            THEORY_OPERATOR_FAMILIES if operator_families is None else operator_families
        )
        self.beam_width = beam_width or min(12, candidate_limit)
        if self.beam_width < 1:
            raise ValueError("beam_width must be positive")
        self.max_revisions = max_revisions
        self.revision_enabled = revision_enabled
        self._theory_sequence = 0

    def _next_theory_id(self) -> str:
        self._theory_sequence += 1
        return f"T{self._theory_sequence:04d}"

    def _enabled(self, name: str) -> bool:
        return name in self.operator_families

    def _new_theory(
        self,
        parent: PartialTheory,
        action: HypothesisAction,
        rules: Sequence[TheoryRule],
    ) -> PartialTheory:
        return parent.evolve(self._next_theory_id(), action, rules=tuple(rules))

    def _initial_theories(
        self, training_pairs: Sequence[TrainingPair], trace: LearningTrace
    ) -> list[PartialTheory]:
        root = PartialTheory.root()
        theories: list[PartialTheory] = []
        base_candidates = [
            candidate
            for candidate in propose_base_hypotheses(training_pairs, self.operator_families)
            if candidate.kind != "dihedral_tile"
        ]
        preferred = [
            candidate
            for candidate in base_candidates
            if candidate.kind
            in {
                "identity",
                "recolor",
                "tile_repeat",
                "dihedral_transform",
                "self_mask_macro_stamp",
                "axis_mode_denoise",
                "self_contained_subset_crop",
                "frame_interior_crop",
                "central_separator_cellwise_combine",
                "adjacent_bilateral_cellwise_combine",
                "distinct_nonbackground_scale",
                "distinct_color_scale",
                "quadrant_odd_one_out",
                "cross_separator_quadrant_reflection_stamp",
                "repeated_panel_odd_one_out_crop",
                "singleton_foreground_border",
                "distinct_color_count_line",
                "separated_panel_cellwise_combine",
                "contiguous_panel_cellwise_combine",
                "unique_component_crop",
                "anti_diagonal_nonbackground_stream",
                "symmetric_foreground_quadrant_crop",
                "uniform_block_self_stamp_fractal",
            }
        ]
        remaining = [
            candidate
            for candidate in base_candidates
            if candidate.kind
            not in {
                "identity",
                "recolor",
                "tile_repeat",
                "mirror",
                "dihedral_transform",
                "self_mask_macro_stamp",
                "axis_mode_denoise",
                "self_contained_subset_crop",
                "frame_interior_crop",
                "central_separator_cellwise_combine",
                "adjacent_bilateral_cellwise_combine",
                "distinct_nonbackground_scale",
                "distinct_color_scale",
                "quadrant_odd_one_out",
                "cross_separator_quadrant_reflection_stamp",
                "repeated_panel_odd_one_out_crop",
                "singleton_foreground_border",
                "distinct_color_count_line",
                "separated_panel_cellwise_combine",
                "contiguous_panel_cellwise_combine",
                "unique_component_crop",
                "anti_diagonal_nonbackground_stream",
                "symmetric_foreground_quadrant_crop",
                "uniform_block_self_stamp_fractal",
            }
        ]
        for candidate in [*preferred, *remaining][: self.candidate_limit]:
            rule = (
                TheoryRule.identity()
                if candidate.kind == "identity"
                else TheoryRule.full_operator(f"rule-{candidate.kind}", candidate)
            )
            action = HypothesisAction(
                ActionKind.ADD_RULE,
                rule.rule_id,
                {"operation": rule.operation, "initial_proposal": True},
            )
            theory = self._new_theory(root, action, (rule,))
            theories.append(theory)
            trace.record(
                ActionKind.PROPOSE,
                stage="initial_generic_theories",
                theory_id=theory.theory_id,
                parent_theory_id=theory.parent_theory_id,
                rule=rule.as_dict(),
            )
        if self._enabled("mirror") or self._enabled("scoped_coordinate_transform"):
            for axis in ("left_right", "top_bottom", "rotate_180"):
                rule = coordinate_transform_rule(f"coordinate-{axis}", axis)
                action = HypothesisAction(
                    ActionKind.ADD_RULE,
                    rule.rule_id,
                    {
                        "operation": "coordinate_transform",
                        "axis": axis,
                        "scope": rule.scope.as_dict(),
                        "initial_proposal": True,
                    },
                )
                theory = self._new_theory(root, action, (rule,))
                theories.append(theory)
                trace.record(
                    ActionKind.PROPOSE,
                    stage="initial_generic_theories",
                    theory_id=theory.theory_id,
                    parent_theory_id=theory.parent_theory_id,
                    rule=rule.as_dict(),
                )
        assessed_theories = [
            (theory, assess_hypothesis(theory, training_pairs)) for theory in theories
        ]
        for theory, assessment in assessed_theories:
            trace.record(
                ActionKind.COMPARE,
                stage="initial_candidate_pre_beam_compatibility",
                theory_id=theory.theory_id,
                **assessment.as_dict(),
            )
        ranked_theories = sorted(
            assessed_theories,
            key=lambda item: (
                not item[1].is_training_exact,
                item[1].contradiction_count,
                item[1].unknown_cell_count,
                -item[1].matching_cell_count,
                item[1].description_length,
                item[0].name,
            ),
        )
        return [theory for theory, _ in ranked_theories[: self.candidate_limit]]

    @staticmethod
    def _demo_information_score(input_grid: Grid, output_grid: Grid) -> tuple[int, int, int]:
        changed = int(difference_summary(input_grid, output_grid)["changed_cell_count"])
        input_colors = {color for row in input_grid for color in row}
        output_colors = {color for row in output_grid for color in row}
        return changed, len(input_colors ^ output_colors), len(input_colors | output_colors)

    def _choose_next_demo(
        self, theory: PartialTheory, training_pairs: Sequence[TrainingPair]
    ) -> tuple[int, str, tuple[int, int, int]] | None:
        observed = set(theory.evaluated_demo_indices)
        candidates = [index for index in range(len(training_pairs)) if index not in observed]
        if not candidates:
            return None
        ranked = sorted(
            (
                (
                    index,
                    self._demo_information_score(*training_pairs[index]),
                )
                for index in candidates
            ),
            key=lambda item: (item[1], -item[0]),
            reverse=True,
        )
        index, score = ranked[0]
        if not observed:
            reason = "initial_highest_observed_change_and_color_discrimination"
        else:
            reason = "unseen_demo_selected_for_residual_version_space_discrimination"
        return index, reason, score

    def _observe_theory(
        self,
        theory: PartialTheory,
        demo_index: int,
        reason: str,
        information_score: tuple[int, int, int],
        training_pairs: Sequence[TrainingPair],
        trace: LearningTrace,
    ) -> PartialTheory:
        input_grid, output_grid = training_pairs[demo_index]
        trace.record(
            ActionKind.CHOOSE_NEXT_DEMO,
            theory_id=theory.theory_id,
            selected_demo=demo_index,
            selection_basis=reason,
            information_score={
                "changed_cells": information_score[0],
                "color_delta": information_score[1],
                "color_inventory": information_score[2],
            },
            previously_observed_demos=list(theory.evaluated_demo_indices),
        )
        evidence = evaluate_theory_demo(theory, demo_index, input_grid, output_grid)
        focus = evidence.counterexamples[0] if evidence.counterexamples else None
        trace.record(
            ActionKind.ATTEND,
            theory_id=theory.theory_id,
            selected_demo=demo_index,
            selected_region=(
                {"row": focus.row, "column": focus.column}
                if focus is not None
                else {"region": "whole_demo"}
            ),
            reason=reason,
        )
        observed = theory.add_demo_evidence(
            evidence,
            HypothesisAction(
                ActionKind.ATTEND,
                f"demo:{demo_index}",
                {"reason": reason, "information_score": information_score},
            ),
        )
        trace.record(
            ActionKind.APPLY_HYPOTHESIS,
            theory_id=observed.theory_id,
            theory_name=observed.name,
            demo_index=demo_index,
            rule_count=len(observed.rules),
            partial_prediction_known_cells=sum(
                cell is not None for row in evidence.partial_prediction for cell in row
            ),
        )
        trace.record(
            ActionKind.COMPARE,
            theory_id=observed.theory_id,
            demo_index=demo_index,
            support=evidence.support.as_dict(),
            explained_cell_count=sum(sum(row) for row in evidence.explained_mask),
            residual_cell_count=sum(sum(row) for row in evidence.residual_mask),
            current_theory=observed.trace_summary(),
        )
        return observed

    @staticmethod
    def _rule_by_id(theory: PartialTheory, rule_id: str | None) -> TheoryRule | None:
        return next((rule for rule in theory.rules if rule.rule_id == rule_id), None)

    @staticmethod
    def _with_identity(rules: Sequence[TheoryRule]) -> tuple[TheoryRule, ...]:
        if any(rule.operation == "identity" for rule in rules):
            return tuple(rules)
        return (TheoryRule.identity(), *rules)

    @staticmethod
    def _has_equivalent_rule(theory: PartialTheory, candidate: TheoryRule) -> bool:
        return any(
            rule.operation == candidate.operation
            and rule.scope == candidate.scope
            and rule.parameters == candidate.parameters
            for rule in theory.rules
        )

    @staticmethod
    def _replace_rule(
        rules: Sequence[TheoryRule], replacement: TheoryRule
    ) -> tuple[TheoryRule, ...]:
        return tuple(
            replacement if rule.rule_id == replacement.rule_id else rule for rule in rules
        )

    @staticmethod
    def _non_background_colors(input_grid: Grid) -> tuple[int, ...]:
        background = min(
            {color for row in input_grid for color in row},
            key=lambda color: (-sum(cell == color for row in input_grid for cell in row), color),
        )
        return tuple(
            sorted({color for row in input_grid for color in row if color != background})
        )

    def _counterexample_revisions(
        self,
        theory: PartialTheory,
        training_pairs: Sequence[TrainingPair],
        trace: LearningTrace,
    ) -> list[PartialTheory]:
        if not theory.counterexamples:
            return []
        counterexample = theory.counterexamples[0]
        evidence = next(
            item for item in theory.demo_evidence if item.demo_index == counterexample.demo_index
        )
        counterexample_index = evidence.counterexamples.index(counterexample)
        responsible_rule_id = evidence.responsible_rule_ids[counterexample_index]
        responsible_rule = self._rule_by_id(theory, responsible_rule_id)
        trace.record(
            ActionKind.FIND_COUNTEREXAMPLE,
            theory_id=theory.theory_id,
            counterexample=counterexample.as_dict(),
            responsible_rule_id=responsible_rule_id,
            responsible_rule=(responsible_rule.as_dict() if responsible_rule else None),
            causal_next_operation="scope_or_rule_revision",
        )
        input_grid, _ = training_pairs[counterexample.demo_index]
        revisions: list[PartialTheory] = []
        if (
            self._enabled("row_span_minimum")
            and responsible_rule is not None
            and responsible_rule.operation == "full_operator"
        ):
            parameters = responsible_rule.parameter_map
            if (
                parameters.get("operator") == "row_span_fill"
                and parameters.get("selection", "all") == "all"
            ):
                revised_parameters = {
                    key: value for key, value in parameters.items() if key != "operator"
                }
                revised_parameters["selection"] = "global_minimum"
                revised_hypothesis = Hypothesis(
                    "row_span_fill",
                    tuple(sorted(revised_parameters.items())),
                    responsible_rule.description_length + 1,
                )
                revised_rule = TheoryRule.full_operator(
                    responsible_rule.rule_id, revised_hypothesis
                )
                action = HypothesisAction(
                    ActionKind.SPECIALIZE,
                    responsible_rule.rule_id,
                    {
                        "counterexample": counterexample.as_dict(),
                        "parameter": "selection",
                        "from_value": "all",
                        "to_value": "global_minimum",
                        "retained_rule_id": responsible_rule.rule_id,
                    },
                )
                child = self._new_theory(
                    theory,
                    action,
                    self._replace_rule(self._with_identity(theory.rules), revised_rule),
                )
                trace.record(
                    ActionKind.ADD_CONDITION,
                    theory_id=child.theory_id,
                    parent_theory_id=theory.theory_id,
                    rule_id=responsible_rule.rule_id,
                    predicate={"parameter": "selection", "value": "global_minimum"},
                    trigger_counterexample=counterexample.as_dict(),
                )
                trace.record(
                    ActionKind.BIND_PARAMETER,
                    theory_id=child.theory_id,
                    rule_id=responsible_rule.rule_id,
                    parameter="selection",
                    value="global_minimum",
                )
                return [child]
        if responsible_rule and responsible_rule.operation == "coordinate_transform":
            axis = str(responsible_rule.parameter_map["axis"])
            colors = self._non_background_colors(input_grid)
            if responsible_rule.scope.kind == "all":
                for color in colors:
                    scoped_rule = responsible_rule.with_scope(ScopePredicate.color(color))
                    scoped_rules = tuple(
                        scoped_rule if rule.rule_id == responsible_rule.rule_id else rule
                        for rule in self._with_identity(theory.rules)
                    )
                    action = HypothesisAction(
                        ActionKind.SPECIALIZE,
                        responsible_rule.rule_id,
                        {
                            "counterexample": counterexample.as_dict(),
                            "from_scope": responsible_rule.scope.as_dict(),
                            "to_scope": scoped_rule.scope.as_dict(),
                            "retained_rule_id": responsible_rule.rule_id,
                        },
                    )
                    child = self._new_theory(theory, action, scoped_rules)
                    revisions.append(child)
                    trace.record(
                        ActionKind.ADD_CONDITION,
                        theory_id=child.theory_id,
                        parent_theory_id=theory.theory_id,
                        rule_id=responsible_rule.rule_id,
                        predicate=scoped_rule.scope.as_dict(),
                        trigger_counterexample=counterexample.as_dict(),
                    )
                    trace.record(
                        ActionKind.CHANGE_SCOPE,
                        theory_id=child.theory_id,
                        rule_id=responsible_rule.rule_id,
                        from_scope=responsible_rule.scope.as_dict(),
                        to_scope=scoped_rule.scope.as_dict(),
                    )
                return revisions
            existing_colors = {
                rule.scope.value
                for rule in theory.rules
                if rule.operation == "coordinate_transform"
                and rule.scope.kind == "color_equals"
                and rule.parameter_map.get("axis") == axis
            }
            for color in colors:
                if color in existing_colors:
                    continue
                added_rule = coordinate_transform_rule(
                    f"coordinate-{axis}-color-{color}", axis, ScopePredicate.color(color)
                )
                action = HypothesisAction(
                    ActionKind.ADD_RULE,
                    added_rule.rule_id,
                    {
                        "counterexample": counterexample.as_dict(),
                        "axis": axis,
                        "scope": added_rule.scope.as_dict(),
                        "retained_rule_ids": [rule.rule_id for rule in theory.rules],
                    },
                )
                child = self._new_theory(
                    theory,
                    action,
                    (*self._with_identity(theory.rules), added_rule),
                )
                revisions.append(child)
                trace.record(
                    ActionKind.EXPLAIN_RESIDUAL,
                    theory_id=child.theory_id,
                    parent_theory_id=theory.theory_id,
                    residual_counterexample=counterexample.as_dict(),
                    added_rule=added_rule.as_dict(),
                )
                trace.record(
                    ActionKind.COMPOSE_RULE,
                    theory_id=child.theory_id,
                    ordered_rule_ids=[rule.rule_id for rule in child.rules],
                )
            if revisions:
                return revisions
        active_coordinate_rule = next(
            (
                rule
                for rule in theory.rules
                if rule.operation == "coordinate_transform" and rule.scope.kind != "all"
            ),
            None,
        )
        if active_coordinate_rule is not None:
            axis = str(active_coordinate_rule.parameter_map["axis"])
            existing_colors = {
                rule.scope.value
                for rule in theory.rules
                if rule.operation == "coordinate_transform"
                and rule.scope.kind == "color_equals"
                and rule.parameter_map.get("axis") == axis
            }
            for color in self._non_background_colors(input_grid):
                if color in existing_colors:
                    continue
                added_rule = coordinate_transform_rule(
                    f"coordinate-{axis}-color-{color}", axis, ScopePredicate.color(color)
                )
                action = HypothesisAction(
                    ActionKind.ADD_RULE,
                    added_rule.rule_id,
                    {
                        "counterexample": counterexample.as_dict(),
                        "axis": axis,
                        "scope": added_rule.scope.as_dict(),
                        "retained_rule_ids": [rule.rule_id for rule in theory.rules],
                        "residual_composition": True,
                    },
                )
                child = self._new_theory(
                    theory,
                    action,
                    (*self._with_identity(theory.rules), added_rule),
                )
                revisions.append(child)
                trace.record(
                    ActionKind.EXPLAIN_RESIDUAL,
                    theory_id=child.theory_id,
                    parent_theory_id=theory.theory_id,
                    residual_counterexample=counterexample.as_dict(),
                    added_rule=added_rule.as_dict(),
                    retained_rule_ids=[rule.rule_id for rule in theory.rules],
                )
                trace.record(
                    ActionKind.COMPOSE_RULE,
                    theory_id=child.theory_id,
                    ordered_rule_ids=[rule.rule_id for rule in child.rules],
                )
            if revisions:
                return revisions
        if (
            counterexample.row >= len(input_grid)
            or counterexample.column >= len(input_grid[0])
        ):
            return revisions
        source_color = input_grid[counterexample.row][counterexample.column]
        if (
            counterexample.observed == background_color(input_grid)
            and source_color != counterexample.observed
        ):
            erase = TheoryRule.erase_color_to_background(
                f"erase-color-{source_color}", source_color
            )
            if not self._has_equivalent_rule(theory, erase):
                action = HypothesisAction(
                    ActionKind.ADD_RULE,
                    erase.rule_id,
                    {
                        "counterexample": counterexample.as_dict(),
                        "proposal_family": "counterexample_erase_to_input_background",
                        "source_color": source_color,
                        "retained_rule_ids": [rule.rule_id for rule in theory.rules],
                    },
                )
                child = self._new_theory(
                    theory,
                    action,
                    (*self._with_identity(theory.rules), erase),
                )
                trace.record(
                    ActionKind.EXPLAIN_RESIDUAL,
                    theory_id=child.theory_id,
                    parent_theory_id=theory.theory_id,
                    residual_counterexample=counterexample.as_dict(),
                    added_rule=erase.as_dict(),
                )
                trace.record(
                    ActionKind.COMPOSE_RULE,
                    theory_id=child.theory_id,
                    ordered_rule_ids=[rule.rule_id for rule in child.rules],
                )
                return [child]
        if source_color != counterexample.observed:
            recolor = recolor_scoped_rule(
                f"recolor-color-{source_color}-to-{counterexample.observed}",
                ScopePredicate.color(source_color),
                counterexample.observed,
            )
            action = HypothesisAction(
                ActionKind.ADD_RULE,
                recolor.rule_id,
                {
                    "counterexample": counterexample.as_dict(),
                    "source_color": source_color,
                    "target_color": counterexample.observed,
                },
            )
            child = self._new_theory(
                theory,
                action,
                (*self._with_identity(theory.rules), recolor),
            )
            revisions.append(child)
            trace.record(
                ActionKind.EXPLAIN_RESIDUAL,
                theory_id=child.theory_id,
                parent_theory_id=theory.theory_id,
                residual_counterexample=counterexample.as_dict(),
                added_rule=recolor.as_dict(),
            )
            trace.record(
                ActionKind.COMPOSE_RULE,
                theory_id=child.theory_id,
                ordered_rule_ids=[rule.rule_id for rule in child.rules],
            )
        return revisions

    def _structural_revisions(
        self,
        theory: PartialTheory,
        training_pairs: Sequence[TrainingPair],
        trace: LearningTrace,
    ) -> list[PartialTheory]:
        if not any(
            family in self.operator_families
            for family in (
                "line_extend",
                "row_span_fill",
                "dihedral_tile",
                "component_property_recolor",
                "component_property_erase",
                "marker_shape_target_recolor",
            )
        ):
            return []
        observed_pairs = [
            training_pairs[index] for index in theory.evaluated_demo_indices
        ]
        if not observed_pairs:
            return []
        revisions: list[PartialTheory] = []
        component_specs = (
            infer_component_property_recolor_specs(observed_pairs)
            if self._enabled("component_property_recolor")
            else ()
        )
        component_erase_specs = (
            infer_component_property_erase_specs(observed_pairs)
            if self._enabled("component_property_erase")
            else ()
        )
        marker_specs = (
            infer_marker_shape_target_recolor_specs(observed_pairs)
            if self._enabled("marker_shape_target_recolor")
            else ()
        )
        if not component_specs and not component_erase_specs and not marker_specs and any(
            family in self.operator_families
            for family in ("line_extend", "row_span_fill", "dihedral_tile")
        ):
            candidates = propose_structural_hypotheses(observed_pairs, self.operator_families)
            ranked_candidates = sorted(
                (
                    (candidate, assess_hypothesis(candidate, observed_pairs))
                    for candidate in candidates
                ),
                key=lambda item: _rank_key(item[1]),
                reverse=True,
            )
            for candidate, assessment in ranked_candidates[: min(self.candidate_limit, self.beam_width)]:
                rule = TheoryRule.full_operator(f"structural-{candidate.kind}", candidate)
                if self._has_equivalent_rule(theory, rule):
                    continue
                action = HypothesisAction(
                    ActionKind.ADD_RULE,
                    rule.rule_id,
                    {
                        "proposal_family": "structural_residual",
                        "operator": candidate.kind,
                        "observed_residual_ranking": {
                            "matching_cell_count": assessment.matching_cell_count,
                            "contradiction_count": assessment.contradiction_count,
                            "unknown_cell_count": assessment.unknown_cell_count,
                        },
                    },
                )
                child = self._new_theory(
                    theory, action, (*self._with_identity(theory.rules), rule)
                )
                revisions.append(child)
                trace.record(
                    ActionKind.SPECIALIZE,
                    theory_id=child.theory_id,
                    parent_theory_id=theory.theory_id,
                    reason="unexplained_residual_proposed_generic_structural_rule",
                    added_rule=rule.as_dict(),
                )
                if candidate.kind == "dihedral_tile":
                    trace.record(
                        ActionKind.EXPLAIN_RESIDUAL,
                        theory_id=child.theory_id,
                        parent_theory_id=theory.theory_id,
                        residual_kind=("contradiction" if theory.counterexamples else "unknown"),
                        added_rule=rule.as_dict(),
                    )
                    trace.record(
                        ActionKind.COMPOSE_RULE,
                        theory_id=child.theory_id,
                        ordered_rule_ids=[item.rule_id for item in child.rules],
                    )
        component_erase_rules = tuple(
            TheoryRule.component_property_erase(
                f"component-erase-{specification.property_name}-{index}",
                specification.property_name,
                specification.values,
            )
            for index, specification in enumerate(component_erase_specs)
        )
        if component_specs:
            for index, specification in enumerate(component_specs):
                existing_rule = next(
                    (
                        item
                        for item in theory.rules
                        if item.operation == "component_property_recolor"
                        and item.parameter_map.get("property") == specification.property_name
                    ),
                    None,
                )
                if existing_rule is None:
                    rule = TheoryRule.component_property_recolor(
                        f"component-property-{specification.property_name}-{index}",
                        specification.property_name,
                        specification.mapping,
                    )
                    action = HypothesisAction(
                        ActionKind.ADD_RULE,
                        rule.rule_id,
                        {
                            "proposal_family": "component_property_residual",
                            "property": specification.property_name,
                            "mapping_count": len(specification.mapping),
                            "observed_demo_count": len(observed_pairs),
                        },
                    )
                    paired_erase = min(
                        component_erase_rules,
                        key=lambda item: (item.description_length, item.name),
                        default=None,
                    )
                    rules = (*self._with_identity(theory.rules), rule)
                    added_erase = (
                        paired_erase is not None
                        and not self._has_equivalent_rule(theory, paired_erase)
                    )
                    if added_erase and paired_erase is not None:
                        rules = (*rules, paired_erase)
                    child = self._new_theory(theory, action, rules)
                    revision_kind = (
                        "new_partial_rule_and_component_erase"
                        if added_erase
                        else "new_partial_rule"
                    )
                else:
                    merged_mapping = deserialize_mapping(
                        str(existing_rule.parameter_map["mapping"])
                    )
                    incompatible = False
                    for property_value, output_color in specification.mapping:
                        previous = merged_mapping.get(property_value)
                        if previous is not None and previous != output_color:
                            incompatible = True
                            break
                        merged_mapping[property_value] = output_color
                    if incompatible or len(merged_mapping) == len(
                        deserialize_mapping(str(existing_rule.parameter_map["mapping"]))
                    ):
                        continue
                    rule = TheoryRule.component_property_recolor(
                        existing_rule.rule_id,
                        specification.property_name,
                        tuple(sorted(merged_mapping.items())),
                    )
                    action = HypothesisAction(
                        ActionKind.BIND_PARAMETER,
                        rule.rule_id,
                        {
                            "proposal_family": "component_property_mapping_revision",
                            "property": specification.property_name,
                            "from_mapping_count": len(
                                deserialize_mapping(str(existing_rule.parameter_map["mapping"]))
                            ),
                            "to_mapping_count": len(merged_mapping),
                            "observed_demo_count": len(observed_pairs),
                        },
                    )
                    child = self._new_theory(
                        theory,
                        action,
                        self._replace_rule(self._with_identity(theory.rules), rule),
                    )
                    added_erase = False
                    revision_kind = "mapping_extension"
                revisions.append(child)
                trace.record(
                    ActionKind.EXPLAIN_RESIDUAL,
                    theory_id=child.theory_id,
                    parent_theory_id=theory.theory_id,
                    residual_kind="contradiction",
                    generic_property=specification.property_name,
                    revision_kind=revision_kind,
                    added_rule=rule.as_dict(),
                )
                if added_erase and paired_erase is not None:
                    trace.record(
                        ActionKind.ADD_RULE,
                        theory_id=child.theory_id,
                        parent_theory_id=theory.theory_id,
                        rule=paired_erase.as_dict(),
                        reason="component_property_consistently_erases_to_input_background",
                    )
                    trace.record(
                        ActionKind.EXPLAIN_RESIDUAL,
                        theory_id=child.theory_id,
                        parent_theory_id=theory.theory_id,
                        residual_kind="contradiction",
                        generic_property=paired_erase.parameter_map["property"],
                        added_rule=paired_erase.as_dict(),
                    )
                trace.record(
                    ActionKind.COMPOSE_RULE,
                    theory_id=child.theory_id,
                    ordered_rule_ids=[item.rule_id for item in child.rules],
                )
        elif component_erase_rules:
            for erase_rule in component_erase_rules:
                if self._has_equivalent_rule(theory, erase_rule):
                    continue
                action = HypothesisAction(
                    ActionKind.ADD_RULE,
                    erase_rule.rule_id,
                    {
                        "proposal_family": "component_property_erase_residual",
                        "property": erase_rule.parameter_map["property"],
                    },
                )
                child = self._new_theory(
                    theory, action, (*self._with_identity(theory.rules), erase_rule)
                )
                revisions.append(child)
                trace.record(
                    ActionKind.EXPLAIN_RESIDUAL,
                    theory_id=child.theory_id,
                    parent_theory_id=theory.theory_id,
                    residual_kind="contradiction",
                    added_rule=erase_rule.as_dict(),
                )
                trace.record(
                    ActionKind.COMPOSE_RULE,
                    theory_id=child.theory_id,
                    ordered_rule_ids=[item.rule_id for item in child.rules],
                )
        if marker_specs:
            for index, specification in enumerate(marker_specs):
                existing_rule = next(
                    (
                        item
                        for item in theory.rules
                        if item.operation == "marker_shape_target_recolor"
                        and item.parameter_map.get("marker_color") == specification.marker_color
                        and item.parameter_map.get("target_color") == specification.target_color
                    ),
                    None,
                )
                erase_rule = TheoryRule.erase_color_to_background(
                    f"erase-color-{specification.marker_color}", specification.marker_color
                )
                if existing_rule is None:
                    rule = TheoryRule.marker_shape_target_recolor(
                        (
                            "marker-shape-target-"
                            f"{specification.marker_color}-{specification.target_color}-{index}"
                        ),
                        specification.marker_color,
                        specification.target_color,
                        specification.mapping,
                    )
                    action = HypothesisAction(
                        ActionKind.ADD_RULE,
                        rule.rule_id,
                        {
                            "proposal_family": "marker_shape_target_residual",
                            "marker_color": specification.marker_color,
                            "target_color": specification.target_color,
                            "mapping_count": len(specification.mapping),
                            "observed_demo_count": len(observed_pairs),
                            "paired_partial_rule": erase_rule.rule_id,
                        },
                    )
                    rules = (*self._with_identity(theory.rules), rule)
                    added_erase = not self._has_equivalent_rule(theory, erase_rule)
                    if added_erase:
                        rules = (*rules, erase_rule)
                    child = self._new_theory(theory, action, rules)
                    revision_kind = "new_partial_relation_and_erase"
                else:
                    merged_mapping = deserialize_mapping(
                        str(existing_rule.parameter_map["mapping"])
                    )
                    incompatible = False
                    for shape, output_color in specification.mapping:
                        previous = merged_mapping.get(shape)
                        if previous is not None and previous != output_color:
                            incompatible = True
                            break
                        merged_mapping[shape] = output_color
                    previous_count = len(
                        deserialize_mapping(str(existing_rule.parameter_map["mapping"]))
                    )
                    if incompatible or len(merged_mapping) == previous_count:
                        continue
                    rule = TheoryRule.marker_shape_target_recolor(
                        existing_rule.rule_id,
                        specification.marker_color,
                        specification.target_color,
                        tuple(sorted(merged_mapping.items())),
                    )
                    action = HypothesisAction(
                        ActionKind.BIND_PARAMETER,
                        rule.rule_id,
                        {
                            "proposal_family": "marker_shape_mapping_revision",
                            "from_mapping_count": previous_count,
                            "to_mapping_count": len(merged_mapping),
                            "observed_demo_count": len(observed_pairs),
                        },
                    )
                    child = self._new_theory(
                        theory,
                        action,
                        self._replace_rule(self._with_identity(theory.rules), rule),
                    )
                    added_erase = False
                    revision_kind = "mapping_extension"
                revisions.append(child)
                trace.record(
                    ActionKind.EXPLAIN_RESIDUAL,
                    theory_id=child.theory_id,
                    parent_theory_id=theory.theory_id,
                    residual_kind="contradiction",
                    generic_relation="marker_shape_to_target_color",
                    revision_kind=revision_kind,
                    added_rule=rule.as_dict(),
                )
                if added_erase:
                    trace.record(
                        ActionKind.ADD_RULE,
                        theory_id=child.theory_id,
                        parent_theory_id=theory.theory_id,
                        rule=erase_rule.as_dict(),
                        reason="marker_cells_are_visible_residuals_to_input_background",
                    )
                    trace.record(
                        ActionKind.EXPLAIN_RESIDUAL,
                        theory_id=child.theory_id,
                        parent_theory_id=theory.theory_id,
                        residual_kind="contradiction",
                        generic_relation="erase_marker_to_input_background",
                        added_rule=erase_rule.as_dict(),
                    )
                trace.record(
                    ActionKind.COMPOSE_RULE,
                    theory_id=child.theory_id,
                    ordered_rule_ids=[item.rule_id for item in child.rules],
                )
        return revisions[: self.candidate_limit]

    @staticmethod
    def _fingerprint(theory: PartialTheory) -> str:
        rules = [
            {
                "operation": rule.operation,
                "scope": rule.scope.as_dict(),
                "parameters": list(rule.parameters),
            }
            for rule in theory.rules
        ]
        return json.dumps(
            {"rules": rules, "evaluated_demos": theory.evaluated_demo_indices},
            sort_keys=True,
        )

    def _push(
        self,
        frontier: list[PartialTheory],
        theory: PartialTheory,
        seen: set[str],
    ) -> None:
        fingerprint = self._fingerprint(theory)
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        frontier.append(theory)
        frontier.sort(key=PartialTheory.priority)
        del frontier[self.beam_width :]

    @staticmethod
    def _complete_prediction(theory: PartialTheory, input_grid: Grid) -> Grid | None:
        prediction = theory.predict(input_grid)
        if any(cell is None for row in prediction for cell in row):
            return None
        return tuple(tuple(int(cell) for cell in row) for row in prediction)

    def _collapse(
        self,
        exact_theories: Sequence[PartialTheory],
        test_inputs: Sequence[Grid],
        trace: LearningTrace,
    ) -> tuple[tuple[Grid, ...], PartialTheory, float] | None:
        groups: dict[str, list[tuple[PartialTheory, tuple[Grid, ...]]]] = {}
        for theory in exact_theories:
            predictions: list[Grid] = []
            for input_grid in test_inputs:
                prediction = self._complete_prediction(theory, input_grid)
                if prediction is None:
                    break
                predictions.append(prediction)
            if len(predictions) != len(test_inputs):
                trace.record(
                    ActionKind.REJECT_RULE,
                    theory_id=theory.theory_id,
                    reason="test_prediction_remains_unknown",
                )
                continue
            complete_predictions = tuple(predictions)
            groups.setdefault(json.dumps(complete_predictions), []).append(
                (theory, complete_predictions)
            )
        if not groups:
            return None
        masses = {
            key: sum(math.exp(-theory.description_length) for theory, _ in entries)
            for key, entries in groups.items()
        }
        total = sum(masses.values())
        selected_key, selected_mass = max(masses.items(), key=lambda item: (item[1], item[0]))
        selected_entries = groups[selected_key]
        theory, predictions = min(
            selected_entries, key=lambda item: (item[0].description_length, item[0].name)
        )
        if len(selected_entries) > 1:
            trace.record(
                ActionKind.MERGE_RULES,
                complete_prediction_group_size=len(selected_entries),
                compatible_theory_ids=[item[0].theory_id for item in selected_entries],
            )
        posterior_mass = selected_mass / total
        trace.record(
            ActionKind.COMMIT,
            selected_hypothesis=theory.name,
            theory_id=theory.theory_id,
            complete_prediction_group_count=len(groups),
            posterior_mass=posterior_mass,
            training_exact=True,
            final_theory=theory.as_dict(include_predictions=False),
        )
        return predictions, theory, posterior_mass

    def solve(self, environment: EvidenceEnvironment, episode_id: str = "arc12-task") -> SolveResult:
        """Learn only from dynamically selected static demonstrations and test inputs."""

        training_pairs = environment.training_pairs
        if not training_pairs:
            raise ValueError("at least one training pair is required")
        self._theory_sequence = 0
        trace = LearningTrace(episode_id)
        frontier: list[PartialTheory] = []
        seen: set[str] = set()
        for theory in self._initial_theories(training_pairs, trace):
            fingerprint = self._fingerprint(theory)
            if fingerprint not in seen:
                seen.add(fingerprint)
                frontier.append(theory)
        exact_theories: list[PartialTheory] = []
        best_theory: PartialTheory | None = None
        revisions = 0
        while frontier and revisions < self.max_revisions:
            theory = frontier.pop(0)
            revisions += 1
            if best_theory is None or theory.priority() < best_theory.priority():
                best_theory = theory
            if theory.counterexamples and self.revision_enabled:
                needs_full_conditional_evidence = any(
                    self._enabled(family)
                    for family in (
                        "component_property_recolor",
                        "component_property_erase",
                        "marker_shape_target_recolor",
                    )
                )
                needs_discriminating_evidence = self._enabled("row_span_minimum")
                required_demo_count = (
                    len(training_pairs)
                    if needs_full_conditional_evidence
                    else 2 if needs_discriminating_evidence else 0
                )
                if len(theory.evaluated_demo_indices) < required_demo_count:
                    next_demo = self._choose_next_demo(theory, training_pairs)
                    if next_demo is not None:
                        demo_index, reason, information_score = next_demo
                        observed = self._observe_theory(
                            theory,
                            demo_index,
                            (
                                "counterexample_requires_visible_conditional_evidence:"
                                f"{reason}"
                            ),
                            information_score,
                            training_pairs,
                            trace,
                        )
                        self._push(frontier, observed, seen)
                        continue
                revisions_from_counterexample = self._counterexample_revisions(
                    theory, training_pairs, trace
                )
                structural_revisions = self._structural_revisions(
                    theory, training_pairs, trace
                )
                if revisions_from_counterexample or structural_revisions:
                    for revised in [*revisions_from_counterexample, *structural_revisions]:
                        self._push(frontier, revised, seen)
                    continue
            next_demo = self._choose_next_demo(theory, training_pairs)
            if next_demo is not None:
                demo_index, reason, information_score = next_demo
                observed = self._observe_theory(
                    theory,
                    demo_index,
                    reason,
                    information_score,
                    training_pairs,
                    trace,
                )
                self._push(frontier, observed, seen)
                continue
            if theory.is_exact_on_observed:
                exact_theories.append(theory)
                trace.record(
                    ActionKind.PROMOTE_CONSTRAINT,
                    theory_id=theory.theory_id,
                    status="complete_training_compatibility_after_revision",
                    rule_count=len(theory.rules),
                    evaluated_demo_count=len(theory.demo_evidence),
                )
                continue
            if self.revision_enabled:
                structural_revisions = self._structural_revisions(theory, training_pairs, trace)
                if structural_revisions:
                    for revised in structural_revisions:
                        self._push(frontier, revised, seen)
                    continue
            trace.record(
                ActionKind.REJECT_RULE,
                theory_id=theory.theory_id,
                reason="no_generic_revision_generated_from_current_observed_residual",
                current_theory=theory.as_dict(include_predictions=False),
            )
        collapsed = self._collapse(exact_theories, environment.test_inputs, trace)
        if collapsed is not None:
            predictions, selected_theory, posterior_mass = collapsed
            return SolveResult(
                predictions=predictions,
                selected_hypothesis=selected_theory.name,
                training_exact=True,
                used_fallback=False,
                posterior_mass=posterior_mass,
                trace=trace.as_dict(),
                final_theory=selected_theory.as_dict(include_predictions=True),
            )
        predictions = tuple(
            tuple(tuple(row) for row in input_grid) for input_grid in environment.test_inputs
        )
        trace.record(
            ActionKind.COMMIT,
            selected_hypothesis="fallback_identity_complete_grid",
            complete_prediction_group_count=0,
            posterior_mass=0.0,
            training_exact=False,
            fallback_reason="no_complete_training_compatible_partial_theory",
            best_partial_theory=(
                best_theory.as_dict(include_predictions=False) if best_theory is not None else None
            ),
        )
        return SolveResult(
            predictions=predictions,
            selected_hypothesis="fallback_identity_complete_grid",
            training_exact=False,
            used_fallback=True,
            posterior_mass=0.0,
            trace=trace.as_dict(),
            final_theory=(
                best_theory.as_dict(include_predictions=True) if best_theory is not None else None
            ),
        )

    @staticmethod
    def _select_external_probe(actions: Sequence[EnvironmentAction]) -> EnvironmentAction | None:
        if not actions:
            return None
        return min(
            actions,
            key=lambda action: (action.action_type, str(action.parameters.get("key", ""))),
        )

    @staticmethod
    def _external_transition_summary(feedback: TransitionFeedback) -> dict[str, object]:
        return {
            "action": feedback.action.as_dict(),
            "accepted": feedback.accepted,
            "changed": feedback.changed,
            "progress": feedback.progress,
            "terminal": feedback.terminal,
            "before_observation": feedback.before.observation_id,
            "after_observation": feedback.after.observation_id,
            "transition_source": feedback.metadata.get("transition_source"),
        }

    @staticmethod
    def _observable_progress(observation: object) -> float | None:
        payload = getattr(observation, "payload", None)
        if not isinstance(payload, dict):
            return None
        value = payload.get("levels_completed")
        return float(value) if isinstance(value, (int, float)) else None

    def run_external_mechanics_episode(
        self,
        world: ObservationWorld,
        public_history: Sequence[TransitionFeedback],
        *,
        max_actions: int,
        episode_id: str = "arc3-public-mechanics",
    ) -> "ExternalMechanicsResult":
        """Learn a public action-motion relation, then act against a visible beacon.

        `public_history` is a bounded sequence of already observed real transitions.
        The learner only receives the current world observation/actions after that
        history and can advance it through `world.act`; it has no access to replay
        records, a simulator, future actions, or post-hoc game rules.
        """

        if max_actions <= 0:
            raise ValueError("external mechanics episodes require a positive action limit")
        self._theory_sequence = 0
        trace = LearningTrace(episode_id)
        initial_observation = world.observe()
        initial_progress = self._observable_progress(initial_observation)
        initial_rule = TheoryRule(
            rule_id="environment-effect",
            operation="environment_transition",
            parameters=(("effect", "action_effects_unknown"),),
            description_length=1,
        )
        initial_action = HypothesisAction(
            ActionKind.ADD_RULE,
            initial_rule.rule_id,
            {
                "effect": "action_effects_unknown",
                "learned_store_initially_empty": True,
                "unobserved_actions_remain_unknown": True,
            },
        )
        theory = self._new_theory(PartialTheory.root(), initial_action, (initial_rule,))
        trace.record(
            ActionKind.ATTEND,
            theory_id=theory.theory_id,
            observation=initial_observation.as_dict(),
            public_history_transition_count=len(public_history),
            live_oracle_visible=False,
            future_transition_visible=False,
        )
        trace.record(
            ActionKind.PROPOSE,
            theory_id=theory.theory_id,
            theory=theory.as_dict(include_predictions=False),
            mechanics_prediction="action effects remain UNKNOWN until observed",
        )
        try:
            motion_model = learn_motion_model(public_history)
        except ValueError as error:
            trace.record(
                ActionKind.REJECT_HYPOTHESIS,
                theory_id=theory.theory_id,
                reason=str(error),
                status="insufficient_public_motion_evidence",
            )
            trace.record(
                ActionKind.COMMIT,
                theory_id=theory.theory_id,
                mechanics_learning_confirmed=False,
                completion_claim="no_external_action_taken_without_a_learned_motion_relation",
            )
            return ExternalMechanicsResult(
                mechanics_learning_confirmed=False,
                goal_directed_action_confirmed=False,
                non_default_action_confirmed=False,
                level_progress_observed=False,
                trace=trace.as_dict(),
                final_theory=theory.as_dict(include_predictions=False),
                history_transition_count=len(public_history),
                transitions=(),
                action_choices=(),
                initial_progress=initial_progress,
                final_progress=initial_progress,
            )
        trace.record(
            ActionKind.APPLY_LOCALLY,
            theory_id=theory.theory_id,
            phase="learn_from_bounded_public_history",
            motion_model=motion_model.as_dict(),
            accepted_history_transition_count=sum(item.accepted for item in public_history),
            changed_history_transition_count=sum(item.changed is True for item in public_history),
        )
        trace.record(
            ActionKind.FIND_COUNTEREXAMPLE,
            theory_id=theory.theory_id,
            counterexample={
                "prior_effect": "action_effects_unknown",
                "observation": "repeatable_action_conditioned_motion",
                "distinct_observed_actions": len(motion_model.action_effects),
            },
            causal_next_operation="specialize_to_observed_action_motion_map",
        )
        motion_rule = initial_rule.with_parameter("effect", "action_motion_map")
        revision_action = HypothesisAction(
            ActionKind.SPECIALIZE,
            motion_rule.rule_id,
            {
                "from_effect": "action_effects_unknown",
                "to_effect": "action_motion_map",
                "source": "bounded_public_history",
            },
        )
        theory = self._new_theory(theory, revision_action, (motion_rule,))
        trace.record(
            ActionKind.SPECIALIZE,
            theory_id=theory.theory_id,
            parent_theory_id=theory.parent_theory_id,
            revised_rule=motion_rule.as_dict(),
        )
        for effect in motion_model.action_effects:
            trace.record(
                ActionKind.BIND_PARAMETER,
                theory_id=theory.theory_id,
                parameter="observed_action_delta",
                action_key=effect.key,
                delta=list(effect.delta),
                support_count=effect.support_count,
            )
        trace.record(
            ActionKind.PROMOTE_CONSTRAINT,
            theory_id=theory.theory_id,
            status="public_action_motion_map_retained",
            controlled_component=motion_model.controlled_component.as_dict(),
            stable_beacon_count=len(motion_model.beacon_signatures),
            unobserved_actions_remain_unknown=True,
        )
        action_choices: list[dict[str, object]] = []
        transitions: list[dict[str, object]] = []
        all_goal_predictions_confirmed = True
        for action_index in range(max_actions):
            current_observation = world.observe()
            choice = choose_goal_directed_action(
                motion_model, current_observation, world.available_actions()
            )
            if choice is None:
                trace.record(
                    ActionKind.REJECT_HYPOTHESIS,
                    theory_id=theory.theory_id,
                    phase="goal_directed_action_selection",
                    reason="no_available_observed_effect_reduces_visible_beacon_relation",
                    action_index=action_index,
                )
                all_goal_predictions_confirmed = False
                break
            trace.record(
                ActionKind.PROPOSE,
                theory_id=theory.theory_id,
                phase="goal_directed_action_selection",
                action_index=action_index,
                choice=choice.as_dict(),
            )
            feedback = world.act(choice.action)
            observed_delta = observed_controlled_delta(
                motion_model, feedback.before, feedback.after
            )
            progress_transition = bool(
                initial_progress is not None
                and feedback.progress is not None
                and feedback.progress > initial_progress
            )
            prediction_matched = feedback.accepted and (
                observed_delta == choice.predicted_delta or progress_transition
            )
            transition_summary = self._external_transition_summary(feedback)
            transition_summary["predicted_controlled_delta"] = list(choice.predicted_delta)
            transition_summary["observed_controlled_delta"] = (
                list(observed_delta) if observed_delta is not None else None
            )
            transition_summary["progress_transition_confirms_goal_contact"] = progress_transition
            transition_summary["prediction_matched"] = prediction_matched
            transitions.append(transition_summary)
            choice_summary = choice.as_dict()
            choice_summary["prediction_matched_observation"] = prediction_matched
            choice_summary["progress_transition_confirms_goal_contact"] = progress_transition
            action_choices.append(choice_summary)
            trace.record(
                ActionKind.APPLY_LOCALLY,
                theory_id=theory.theory_id,
                phase="goal_directed_external_action",
                action_index=action_index,
                choice=choice.as_dict(),
                transition=transition_summary,
            )
            trace.record(
                ActionKind.COMPARE,
                theory_id=theory.theory_id,
                action_index=action_index,
                predicted_controlled_delta=list(choice.predicted_delta),
                observed_controlled_delta=(
                    list(observed_delta) if observed_delta is not None else None
                ),
                predicted_goal_distance_before=choice.goal_distance_before,
                predicted_goal_distance_after=choice.goal_distance_after,
                transition_accepted=feedback.accepted,
                prediction_matched_observation=prediction_matched,
                observed_progress=feedback.progress,
                progress_transition_confirms_goal_contact=progress_transition,
            )
            if not prediction_matched:
                all_goal_predictions_confirmed = False
                trace.record(
                    ActionKind.FIND_COUNTEREXAMPLE,
                    theory_id=theory.theory_id,
                    action_index=action_index,
                    counterexample={
                        "predicted_delta": list(choice.predicted_delta),
                        "observed_delta": (
                            list(observed_delta) if observed_delta is not None else None
                        ),
                        "transition_accepted": feedback.accepted,
                    },
                )
                break
            current_progress = self._observable_progress(feedback.after)
            if (
                initial_progress is not None
                and current_progress is not None
                and current_progress > initial_progress
            ):
                trace.record(
                    ActionKind.PROMOTE_CONSTRAINT,
                    theory_id=theory.theory_id,
                    status="recorded_goal_directed_actions_contributed_to_level_progress",
                    initial_progress=initial_progress,
                    observed_progress=current_progress,
                )
                break
        final_observation = world.observe()
        final_progress = self._observable_progress(final_observation)
        mechanics_learning_confirmed = len(motion_model.action_effects) >= 2
        non_default_action_confirmed = any(
            bool(choice.get("is_non_default")) for choice in action_choices
        )
        level_progress_observed = bool(
            initial_progress is not None
            and final_progress is not None
            and final_progress > initial_progress
        )
        goal_directed_action_confirmed = bool(
            action_choices
            and all_goal_predictions_confirmed
            and all(
                choice["goal_distance_after"] < choice["goal_distance_before"]
                for choice in action_choices
            )
        )
        final_theory = theory.as_dict(include_predictions=False)
        final_theory["learned_motion_model"] = motion_model.as_dict()
        trace.record(
            ActionKind.COMMIT,
            theory_id=theory.theory_id,
            selected_hypothesis=motion_rule.name,
            mechanics_learning_confirmed=mechanics_learning_confirmed,
            goal_directed_action_confirmed=goal_directed_action_confirmed,
            non_default_action_confirmed=non_default_action_confirmed,
            level_progress_observed=level_progress_observed,
            completion_claim=(
                "source_pinned_recorded_replay_mechanics_evidence_not_a_general_arc3_solver"
            ),
            final_theory=final_theory,
        )
        return ExternalMechanicsResult(
            mechanics_learning_confirmed=mechanics_learning_confirmed,
            goal_directed_action_confirmed=goal_directed_action_confirmed,
            non_default_action_confirmed=non_default_action_confirmed,
            level_progress_observed=level_progress_observed,
            trace=trace.as_dict(),
            final_theory=final_theory,
            history_transition_count=len(public_history),
            transitions=tuple(transitions),
            action_choices=tuple(action_choices),
            initial_progress=initial_progress,
            final_progress=final_progress,
        )

    def run_external_probe(
        self, world: ObservationWorld, episode_id: str = "arc3-public-transition-probe"
    ) -> "ExternalProbeResult":
        """Run one observable probe/revision/exploit loop over any external-action world.

        The initial state has no learned game rule. It proposes only that an action
        leaves the observation static, then revises that generic claim if a real
        transition refutes it. This is an architecture experiment, not a game solve.
        """

        self._theory_sequence = 0
        trace = LearningTrace(episode_id)
        initial_observation = world.observe()
        initial_rule = TheoryRule(
            rule_id="environment-effect",
            operation="environment_transition",
            parameters=(("effect", "state_static"),),
            description_length=1,
        )
        initial_action = HypothesisAction(
            ActionKind.ADD_RULE,
            initial_rule.rule_id,
            {"effect": "state_static", "learned_store_initially_empty": True},
        )
        theory = self._new_theory(PartialTheory.root(), initial_action, (initial_rule,))
        trace.record(
            ActionKind.ATTEND,
            theory_id=theory.theory_id,
            observation=initial_observation.as_dict(),
            live_oracle_visible=False,
        )
        trace.record(
            ActionKind.PROPOSE,
            theory_id=theory.theory_id,
            theory=theory.as_dict(include_predictions=False),
            mechanics_prediction="selected_external_action_leaves_observation_static",
        )
        first_action = self._select_external_probe(world.available_actions())
        if first_action is None:
            trace.record(
                ActionKind.COMMIT,
                theory_id=theory.theory_id,
                status="no_public_action_available_for_probe",
                external_probe_confirmed=False,
            )
            return ExternalProbeResult(
                external_probe_confirmed=False,
                trace=trace.as_dict(),
                final_theory=theory.as_dict(include_predictions=False),
                transitions=(),
            )
        first_feedback = world.act(first_action)
        trace.record(
            ActionKind.APPLY_LOCALLY,
            theory_id=theory.theory_id,
            phase="deliberate_external_probe",
            transition=first_feedback.as_dict(),
        )
        trace.record(
            ActionKind.COMPARE,
            theory_id=theory.theory_id,
            predicted_state_change=False,
            observed_state_change=first_feedback.changed,
            transition_accepted=first_feedback.accepted,
        )
        transitions: list[TransitionFeedback] = [first_feedback]
        confirmed = False
        if first_feedback.accepted and first_feedback.changed is True:
            trace.record(
                ActionKind.FIND_COUNTEREXAMPLE,
                theory_id=theory.theory_id,
                counterexample={
                    "prediction": "state_static",
                    "observation": "state_changed",
                    "external_action": first_action.as_dict(),
                },
                causal_next_operation="revise_environment_effect_parameter",
            )
            revised_rule = initial_rule.with_parameter("effect", "state_change_possible")
            revision_action = HypothesisAction(
                ActionKind.SPECIALIZE,
                revised_rule.rule_id,
                {
                    "from_effect": "state_static",
                    "to_effect": "state_change_possible",
                    "trigger": "observed_public_transition",
                },
            )
            theory = self._new_theory(theory, revision_action, (revised_rule,))
            trace.record(
                ActionKind.SPECIALIZE,
                theory_id=theory.theory_id,
                parent_theory_id=theory.parent_theory_id,
                revised_rule=revised_rule.as_dict(),
            )
            trace.record(
                ActionKind.BIND_PARAMETER,
                theory_id=theory.theory_id,
                parameter="effect",
                value="state_change_possible",
            )
            exploit_action = self._select_external_probe(world.available_actions())
            if exploit_action is not None:
                exploit_feedback = world.act(exploit_action)
                transitions.append(exploit_feedback)
                trace.record(
                    ActionKind.APPLY_LOCALLY,
                    theory_id=theory.theory_id,
                    phase="exploit_confirmed_effect_hypothesis",
                    transition=exploit_feedback.as_dict(),
                )
                trace.record(
                    ActionKind.COMPARE,
                    theory_id=theory.theory_id,
                    predicted_state_change=True,
                    observed_state_change=exploit_feedback.changed,
                    transition_accepted=exploit_feedback.accepted,
                )
                confirmed = exploit_feedback.accepted and exploit_feedback.changed is True
        if confirmed:
            trace.record(
                ActionKind.PROMOTE_CONSTRAINT,
                theory_id=theory.theory_id,
                status="two_real_observed_transitions_support_state_change_possible",
            )
        trace.record(
            ActionKind.COMMIT,
            theory_id=theory.theory_id,
            selected_hypothesis=theory.name,
            external_probe_confirmed=confirmed,
            completion_claim="not_an_arc3_game_solve",
            final_theory=theory.as_dict(include_predictions=False),
        )
        return ExternalProbeResult(
            external_probe_confirmed=confirmed,
            trace=trace.as_dict(),
            final_theory=theory.as_dict(include_predictions=False),
            transitions=tuple(item.as_dict() for item in transitions),
        )


@dataclass(frozen=True)
class ExternalProbeResult:
    """Auditable result of a shared-core external-action hypothesis experiment."""

    external_probe_confirmed: bool
    trace: dict[str, object]
    final_theory: dict[str, object]
    transitions: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class ExternalMechanicsResult:
    """Auditable bounded-history mechanics-learning result for an external replay."""

    mechanics_learning_confirmed: bool
    goal_directed_action_confirmed: bool
    non_default_action_confirmed: bool
    level_progress_observed: bool
    trace: dict[str, object]
    final_theory: dict[str, object]
    history_transition_count: int
    transitions: tuple[dict[str, object], ...]
    action_choices: tuple[dict[str, object], ...]
    initial_progress: float | None
    final_progress: float | None
