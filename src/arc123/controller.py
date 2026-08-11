"""A deterministic non-VLM controller for iterative hypothesis learning."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from .compatibility import assess_hypothesis
from .contracts import EnvironmentAction, HypothesisAction, ObservationWorld, TransitionFeedback
from .hypotheses import Hypothesis, propose_base_hypotheses, propose_structural_hypotheses
from .model import ActionKind, Grid, HypothesisAssessment, PartialGrid, SolveResult, TrainingPair
from .perceptions import difference_summary
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
    "translate",
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
    "line_extend",
    "row_span_fill",
    "scoped_coordinate_transform",
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
            if candidate.kind in {"identity", "recolor", "tile_repeat"}
        ]
        remaining = [
            candidate
            for candidate in base_candidates
            if candidate.kind not in {"identity", "recolor", "tile_repeat", "mirror"}
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
        def initial_priority(theory: PartialTheory) -> tuple[int, str]:
            rule = theory.rules[0]
            if rule.operation == "coordinate_transform":
                return 1, theory.theory_id
            if rule.operation == "identity" or theory.name.startswith(("recolor(", "tile_repeat(")):
                return 0, theory.theory_id
            return 2, theory.theory_id

        return sorted(theories, key=initial_priority)[: self.candidate_limit]

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
            for family in ("line_extend", "row_span_fill", "dihedral_tile")
        ):
            return []
        if any(
            action.parameters.get("proposal_family") == "structural_residual"
            for action in theory.history
        ):
            return []
        observed_pairs = [
            training_pairs[index] for index in theory.evaluated_demo_indices
        ]
        if not observed_pairs:
            return []
        candidates = propose_structural_hypotheses(observed_pairs, self.operator_families)
        ranked_candidates = sorted(
            (
                (candidate, assess_hypothesis(candidate, observed_pairs))
                for candidate in candidates
            ),
            key=lambda item: _rank_key(item[1]),
            reverse=True,
        )
        revisions: list[PartialTheory] = []
        for candidate, assessment in ranked_candidates[: min(self.candidate_limit, self.beam_width)]:
            rule = TheoryRule.full_operator(f"structural-{candidate.kind}", candidate)
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
            child = self._new_theory(theory, action, (*theory.rules, rule))
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
        return revisions

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
            self._push(frontier, theory, seen)
        exact_theories: list[PartialTheory] = []
        best_theory: PartialTheory | None = None
        revisions = 0
        while frontier and revisions < self.max_revisions:
            theory = frontier.pop(0)
            revisions += 1
            if best_theory is None or theory.priority() < best_theory.priority():
                best_theory = theory
            if theory.counterexamples:
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
