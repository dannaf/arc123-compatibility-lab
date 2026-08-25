"""Robust rectangular-enclosure semantic hypotheses.

The transform primitive is "fill selected cells inside a rectangular frame".
Which frame descriptor controls the fill color is *not* hard-coded: visible
training examples are converted to semantic observations and the generic
callosal separator learner chooses a minimum deterministic descriptor subset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .callosal_separator import SemanticObservation, SeparatorModel, learn_minimal_separator
from .model import Grid, PartialGrid, TrainingPair
from .perceptions import connected_components


def _is_rectangular_frame(component) -> bool:
    row0, column0, row1, column1 = component.bbox
    if row1 - row0 + 1 < 3 or column1 - column0 + 1 < 3:
        return False
    perimeter = {
        (row, column)
        for row in range(row0, row1 + 1)
        for column in range(column0, column1 + 1)
        if row in {row0, row1} or column in {column0, column1}
    }
    return set(component.cells) == perimeter


def _frames(grid: Grid):
    return tuple(
        component
        for component in connected_components(grid, include_background=True)
        if _is_rectangular_frame(component)
    )


def _frame_descriptors(frame) -> dict[str, int]:
    row0, column0, row1, column1 = frame.bbox
    height = row1 - row0 + 1
    width = column1 - column0 + 1
    return {
        "frame_color": frame.color,
        "frame_height": height,
        "frame_width": width,
        "interior_area": (height - 2) * (width - 2),
        "interior_height": height - 2,
        "interior_width": width - 2,
    }


@dataclass(frozen=True)
class LearnedRectangularEnclosureAreaFill:
    """Compatibility shim for direct area->fill fixtures."""

    mapping: tuple[tuple[int, int], ...]
    fillable_input_value: Optional[int] = None
    name: str = "rectangular_enclosure_area_fill"
    description_length: int = 5

    def _infer_fillable_for_grid(self, input_grid: Grid) -> Optional[int]:
        if self.fillable_input_value is not None:
            return self.fillable_input_value
        counts: dict[int, int] = {}
        for frame in _frames(input_grid):
            row0, column0, row1, column1 = frame.bbox
            for row in range(row0 + 1, row1):
                for column in range(column0 + 1, column1):
                    value = input_grid[row][column]
                    if value == frame.color:
                        continue
                    counts[value] = counts.get(value, 0) + 1
        if not counts:
            return None
        best = max(counts.values())
        winners = [value for value, count in counts.items() if count == best]
        return winners[0] if len(winners) == 1 else None

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "frame_interior_area<->fill_color",
            "descriptor_names": ("interior_area",),
            "forward_rows": len(self.mapping),
            "forward_deterministic": True,
            "background_guardrail": "fillable value not inferred from global modal color",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        fillable = self._infer_fillable_for_grid(input_grid)
        output: list[list[Optional[int]]] = [list(row) for row in input_grid]
        if fillable is None:
            return tuple(tuple(row) for row in output)
        learned = dict(self.mapping)
        for frame in _frames(input_grid):
            fill = learned.get(_frame_descriptors(frame)["interior_area"])
            row0, column0, row1, column1 = frame.bbox
            for row in range(row0 + 1, row1):
                for column in range(column0 + 1, column1):
                    if input_grid[row][column] == fillable:
                        output[row][column] = fill if fill is not None else None
        return tuple(tuple(row) for row in output)


@dataclass(frozen=True)
class DiscoveredRectangularEnclosureFill:
    """Rectangular fill whose causal semantic key was discovered generically."""

    separator: SeparatorModel
    fillable_input_value: int
    name: str = "rectangular_enclosure_area_fill"
    description_length: int = 5

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "frame_descriptors<->fill_color",
            "fillable_input_value": self.fillable_input_value,
            "separator": self.separator.callosal_summary,
            "background_guardrail": "fillable value learned from changed training cells",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        output: list[list[Optional[int]]] = [list(row) for row in input_grid]
        for frame in _frames(input_grid):
            fill = self.separator.predict(_frame_descriptors(frame))
            row0, column0, row1, column1 = frame.bbox
            for row in range(row0 + 1, row1):
                for column in range(column0 + 1, column1):
                    if input_grid[row][column] != self.fillable_input_value:
                        continue
                    output[row][column] = fill if fill is not None else None
        return tuple(tuple(row) for row in output)


def propose_rectangle_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[DiscoveredRectangularEnclosureFill]:
    if enabled_operator_families is not None and (
        "rectangular_enclosure_area_fill" not in enabled_operator_families
        and "enclosed_background_fill" not in enabled_operator_families
    ):
        return []
    if not training_pairs:
        return []

    learned_fillable: Optional[int] = None
    observations: list[SemanticObservation] = []
    saw_explained_change = False

    for input_grid, output_grid in training_pairs:
        if len(input_grid) != len(output_grid) or len(input_grid[0]) != len(output_grid[0]):
            return []
        frame_list = _frames(input_grid)
        if not frame_list:
            return []
        covered_changes: set[tuple[int, int]] = set()

        for frame in frame_list:
            row0, column0, row1, column1 = frame.bbox
            changes = []
            for row in range(row0 + 1, row1):
                for column in range(column0 + 1, column1):
                    before = input_grid[row][column]
                    after = output_grid[row][column]
                    if before != after:
                        changes.append((row, column, before, after))
            if not changes:
                continue

            before_values = {before for _, _, before, _ in changes}
            after_values = {after for _, _, _, after in changes}
            if len(before_values) != 1 or len(after_values) != 1:
                return []
            fillable = next(iter(before_values))
            fill = next(iter(after_values))
            if fillable == frame.color:
                return []
            if learned_fillable is None:
                learned_fillable = fillable
            elif learned_fillable != fillable:
                return []
            observations.append(SemanticObservation(_frame_descriptors(frame), fill))
            covered_changes.update((row, column) for row, column, _, _ in changes)
            saw_explained_change = True

        all_changes = {
            (row, column)
            for row in range(len(input_grid))
            for column in range(len(input_grid[0]))
            if input_grid[row][column] != output_grid[row][column]
        }
        if all_changes != covered_changes:
            return []

    if not saw_explained_change or learned_fillable is None:
        return []

    separator = learn_minimal_separator(
        observations,
        (
            "frame_color",
            "frame_height",
            "frame_width",
            "interior_area",
            "interior_height",
            "interior_width",
        ),
        max_arity=2,
    )
    if separator is None:
        return []

    candidate = DiscoveredRectangularEnclosureFill(separator, learned_fillable)
    if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
        return [candidate]
    return []
