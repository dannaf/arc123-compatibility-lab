"""Exact observed support and UNKNOWN-preserving compatibility evaluation."""

from __future__ import annotations

from typing import Optional, Protocol, Sequence

from .model import (
    CompatibilityFeedback,
    Counterexample,
    Grid,
    HypothesisAssessment,
    PartialGrid,
    SupportState,
    TrainingPair,
)


MAX_REPORTED_COUNTEREXAMPLES = 1


class PartialPredictor(Protocol):
    name: str
    description_length: int

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]: ...


def evaluate_partial_prediction(
    demo_index: int, prediction: Optional[PartialGrid], observed_output: Grid
) -> CompatibilityFeedback:
    if prediction is None:
        return CompatibilityFeedback(
            demo_index=demo_index,
            asserted_cell_count=0,
            matching_cell_count=0,
            contradiction_count=0,
            unknown_cell_count=len(observed_output) * len(observed_output[0]),
            support_state=SupportState.UNKNOWN,
            counterexamples=(),
        )
    if len(prediction) != len(observed_output) or any(
        len(predicted_row) != len(observed_row)
        for predicted_row, observed_row in zip(prediction, observed_output)
    ):
        return CompatibilityFeedback(
            demo_index=demo_index,
            asserted_cell_count=0,
            matching_cell_count=0,
            contradiction_count=0,
            unknown_cell_count=len(observed_output) * len(observed_output[0]),
            support_state=SupportState.UNKNOWN,
            counterexamples=(),
        )
    asserted = 0
    matching = 0
    counterexamples: list[Counterexample] = []
    contradiction_count = 0
    unknown = 0
    for row_index, (prediction_row, observed_row) in enumerate(
        zip(prediction, observed_output)
    ):
        for column_index, (predicted, observed) in enumerate(
            zip(prediction_row, observed_row)
        ):
            if predicted is None:
                unknown += 1
            elif predicted == observed:
                asserted += 1
                matching += 1
            else:
                asserted += 1
                contradiction_count += 1
                if len(counterexamples) < MAX_REPORTED_COUNTEREXAMPLES:
                    counterexamples.append(
                        Counterexample(demo_index, row_index, column_index, predicted, observed)
                    )
    if contradiction_count:
        state = SupportState.IMPOSSIBLE
    elif unknown:
        state = SupportState.UNKNOWN
    else:
        state = SupportState.COMPATIBLE
    return CompatibilityFeedback(
        demo_index=demo_index,
        asserted_cell_count=asserted,
        matching_cell_count=matching,
        contradiction_count=contradiction_count,
        unknown_cell_count=unknown,
        support_state=state,
        counterexamples=tuple(counterexamples),
    )


def assess_hypothesis(
    hypothesis: PartialPredictor, training_pairs: Sequence[TrainingPair]
) -> HypothesisAssessment:
    feedback = tuple(
        evaluate_partial_prediction(demo_index, hypothesis.predict(input_grid), output_grid)
        for demo_index, (input_grid, output_grid) in enumerate(training_pairs)
    )
    return HypothesisAssessment(
        hypothesis_name=hypothesis.name,
        description_length=hypothesis.description_length,
        feedback=feedback,
    )
