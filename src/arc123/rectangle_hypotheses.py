"""Robust rectangular-enclosure semantic hypotheses.

Unlike the first prototype in semantic_hypotheses.py, this implementation does
not equate the grid's modal color with background.  ARC task 00dbd492 is a
counterexample: the rectangular frame color can itself be the modal color.
The fillable interior input value is therefore learned directly from changed
training cells, and frame detection considers components of every color.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

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
    # include_background=True means "consider every color", not "assume the
    # modal color is semantic background".  This is essential when the frame
    # itself is the global mode.
    return tuple(
        component
        for component in connected_components(grid, include_background=True)
        if _is_rectangular_frame(component)
    )


@dataclass(frozen=True)
class LearnedRectangularEnclosureAreaFill:
    """Map frame interior area to fill color for one learned fillable input value."""

    mapping: tuple[tuple[int, int], ...]
    fillable_input_value: Optional[int] = None
    name: str = "rectangular_enclosure_area_fill"
    description_length: int = 5

    @property
    def callosal_summary(self) -> dict[str, object]:
        reverse: dict[int, list[int]] = {}
        for area, color in self.mapping:
            reverse.setdefault(color, []).append(area)
        return {
            "interface": "(frame_interior_area,fillable_input_value)<->fill_color",
            "forward_rows": len(self.mapping),
            "fillable_input_value": self.fillable_input_value,
            "forward_deterministic": True,
            "backward_deterministic": all(len(areas) == 1 for areas in reverse.values()),
            "background_guardrail": "fillable value learned from training changes; global mode not assumed",
        }

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

    def predict(self, input_grid: Grid) -> PartialGrid:
        learned = dict(self.mapping)
        fillable = self._infer_fillable_for_grid(input_grid)
        output: list[list[Optional[int]]] = [list(row) for row in input_grid]
        if fillable is None:
            return tuple(tuple(row) for row in output)
        for frame in _frames(input_grid):
            row0, column0, row1, column1 = frame.bbox
            area = (row1 - row0 - 1) * (column1 - column0 - 1)
            fill = learned.get(area)
            for row in range(row0 + 1, row1):
                for column in range(column0 + 1, column1):
                    if input_grid[row][column] != fillable:
                        continue
                    output[row][column] = fill if fill is not None else None
        return tuple(tuple(row) for row in output)


def propose_rectangle_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[LearnedRectangularEnclosureAreaFill]:
    if enabled_operator_families is not None and (
        "rectangular_enclosure_area_fill" not in enabled_operator_families
        and "enclosed_background_fill" not in enabled_operator_families
    ):
        return []
    if not training_pairs:
        return []

    mapping: dict[int, int] = {}
    learned_fillable: Optional[int] = None
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
            area = (row1 - row0 - 1) * (column1 - column0 - 1)
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
            prior = mapping.get(area)
            if prior is not None and prior != fill:
                return []
            mapping[area] = fill
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

    if not saw_explained_change or learned_fillable is None or not mapping:
        return []

    candidate = LearnedRectangularEnclosureAreaFill(
        tuple(sorted(mapping.items())), learned_fillable
    )
    if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
        return [candidate]
    return []
