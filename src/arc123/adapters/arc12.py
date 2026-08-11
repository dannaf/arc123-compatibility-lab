"""Static ARC1/2 demonstrations presented as a latent-interaction environment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from ..compatibility import evaluate_partial_prediction
from ..model import CompatibilityFeedback, Grid, PartialGrid, TrainingPair, grid_from, grid_to_lists
from ..perceptions import connected_components


@dataclass(frozen=True)
class ARC12InteractiveEnv:
    """Evidence world with visible training outcomes and hidden test targets.

    `post_answer_validate` is deliberately outside the controller-facing view. The
    controller can inspect demonstrations repeatedly, but cannot access a held-out
    test target before it commits a complete grid.
    """

    _training_pairs: tuple[TrainingPair, ...]
    _test_inputs: tuple[Grid, ...]
    _test_targets: tuple[Optional[Grid], ...]
    _provenance: Mapping[str, Any]

    @classmethod
    def from_task_payload(
        cls, payload: Mapping[str, Any], provenance: Optional[Mapping[str, Any]] = None
    ) -> "ARC12InteractiveEnv":
        train = payload.get("train")
        test = payload.get("test")
        if not isinstance(train, list) or not train:
            raise ValueError("ARC12 task requires non-empty train examples")
        if not isinstance(test, list) or not test:
            raise ValueError("ARC12 task requires non-empty test examples")
        training_pairs: list[TrainingPair] = []
        for index, pair in enumerate(train):
            if not isinstance(pair, Mapping):
                raise ValueError(f"train[{index}] must be an object")
            training_pairs.append(
                (
                    grid_from(pair.get("input"), f"train[{index}].input"),
                    grid_from(pair.get("output"), f"train[{index}].output"),
                )
            )
        test_inputs: list[Grid] = []
        test_targets: list[Optional[Grid]] = []
        for index, test_case in enumerate(test):
            if not isinstance(test_case, Mapping):
                raise ValueError(f"test[{index}] must be an object")
            test_inputs.append(grid_from(test_case.get("input"), f"test[{index}].input"))
            target = test_case.get("output")
            test_targets.append(
                grid_from(target, f"test[{index}].output") if target is not None else None
            )
        return cls(
            tuple(training_pairs),
            tuple(test_inputs),
            tuple(test_targets),
            dict(provenance or {}),
        )

    @property
    def training_pairs(self) -> tuple[TrainingPair, ...]:
        return self._training_pairs

    @property
    def test_inputs(self) -> tuple[Grid, ...]:
        return self._test_inputs

    def agent_view(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "training_pairs": [
                {"input": grid_to_lists(input_grid), "output": grid_to_lists(output_grid)}
                for input_grid, output_grid in self._training_pairs
            ],
            "test_inputs": [grid_to_lists(grid) for grid in self._test_inputs],
            "test_targets_visible": False,
            "task_id_visible": False,
        }

    def inspect_demo(self, demo_index: int) -> dict[str, Any]:
        input_grid, output_grid = self._training_pairs[demo_index]
        return {
            "demo_index": demo_index,
            "input": grid_to_lists(input_grid),
            "output": grid_to_lists(output_grid),
        }

    def query_regions(
        self, demo_index: int, side: str, connectivity: int = 4
    ) -> list[dict[str, Any]]:
        input_grid, output_grid = self._training_pairs[demo_index]
        if side == "input":
            grid = input_grid
        elif side == "output":
            grid = output_grid
        else:
            raise ValueError("side must be 'input' or 'output'")
        return [
            {
                "color": component.color,
                "cells": [list(cell) for cell in component.cells],
                "bbox": list(component.bbox),
                "area": component.area,
            }
            for component in connected_components(grid, connectivity)
        ]

    def compatibility_feedback(
        self, demo_index: int, prediction: Optional[PartialGrid]
    ) -> CompatibilityFeedback:
        return evaluate_partial_prediction(
            demo_index, prediction, self._training_pairs[demo_index][1]
        )

    def post_answer_validate(self, predictions: Sequence[Grid]) -> list[dict[str, Any]]:
        if len(predictions) != len(self._test_targets):
            raise ValueError("prediction count must equal test-case count")
        results: list[dict[str, Any]] = []
        for test_index, (prediction, target) in enumerate(
            zip(predictions, self._test_targets)
        ):
            if target is None:
                raise ValueError("post-answer V&V requires a visible evaluator target")
            shape_matches = len(prediction) == len(target) and len(prediction[0]) == len(target[0])
            mismatches = (
                sum(
                    predicted != observed
                    for prediction_row, target_row in zip(prediction, target)
                    for predicted, observed in zip(prediction_row, target_row)
                )
                if shape_matches
                else len(target) * len(target[0])
            )
            results.append(
                {
                    "test_index": test_index,
                    "all_cells_match": shape_matches and mismatches == 0,
                    "mismatched_cell_count": mismatches,
                    "compared_position_count": len(target) * len(target[0]),
                    "prediction": grid_to_lists(prediction),
                    "expected_output": grid_to_lists(target),
                }
            )
        return results

    def provenance_for_report(self) -> dict[str, Any]:
        return dict(self._provenance)
