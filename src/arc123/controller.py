"""A deterministic non-VLM controller for iterative hypothesis learning."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from .compatibility import assess_hypothesis
from .cross_object_bridge_hypotheses import propose_cross_object_bridge_hypotheses
from .frequency_macro_hypotheses import propose_frequency_macro_hypotheses
from .generic_object_hypotheses import propose_generic_object_hypotheses
from .hypotheses import Hypothesis, propose_base_hypotheses, propose_structural_hypotheses
from .model import ActionKind, Grid, HypothesisAssessment, PartialGrid, SolveResult, TrainingPair
from .partition_hypotheses import propose_partition_hypotheses
from .perceptions import difference_summary
from .rectangle_hypotheses import propose_rectangle_hypotheses
from .relational_tiling_hypotheses import propose_relational_tiling_hypotheses
from .semantic_hypotheses import propose_semantic_hypotheses
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
    "row_marker_column_to_constant_row",
    "column_downward_propagation",
    "enclosed_background_fill",
    "rectangular_enclosure_area_fill",
    "macro_micro_gate",
    "row_column_permutation_completion",
    "alternating_mirror_tile",
    "cross_object_bridge",
    "partition_cell_semantic_label",
    "component_select_extract",
    "unique_neighbor_component_propagation",
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
                for predicted, input_color in zip(prediction_row, input_row)
            )
            for prediction_row, input_row in zip(prediction, input_grid)
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


class IterativeHypothesisLearner:
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
            metadata = {}
            callosal_summary = getattr(candidate, "callosal_summary", None)
            if callosal_summary is not None:
                metadata["callosal_summary"] = callosal_summary
            trace.record(
                ActionKind.APPLY_HYPOTHESIS,
                stage=stage,
                hypothesis=candidate.name,
                description_length=candidate.description_length,
                **metadata,
            )
            trace.record(ActionKind.COMPARE, stage=stage, **assessment.as_dict())
            if assessment.is_training_exact:
                exact.append((candidate, assessment))
                trace.record(
                    ActionKind.PROMOTE_CONSTRAINT,
                    stage=stage,
                    hypothesis=candidate.name,
                    status="full_training_compatibility",
                    **metadata,
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
                    **metadata,
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
        if not exact:
            trace.record(
                ActionKind.SPECIALIZE,
                reason="no_low_level_training_complete_hypothesis",
                retained_partial_hypothesis_count=len(partial),
                next_operator_family="semantic_callosal_interfaces",
            )
            semantic_candidates = [
                *propose_semantic_hypotheses(training_pairs, self.operator_families),
                *propose_rectangle_hypotheses(training_pairs, self.operator_families),
                *propose_frequency_macro_hypotheses(training_pairs, self.operator_families),
                *propose_relational_tiling_hypotheses(training_pairs, self.operator_families),
                *propose_cross_object_bridge_hypotheses(training_pairs, self.operator_families),
                *propose_partition_hypotheses(training_pairs, self.operator_families),
                *propose_generic_object_hypotheses(training_pairs, self.operator_families),
            ]
            self._evaluate_stage(
                "semantic_callosal_interfaces",
                semantic_candidates,
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
