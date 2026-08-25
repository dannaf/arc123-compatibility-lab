"""Cross-object bridge hypotheses for relational ARC transformations.

A typed mirror-copy transform is available, but the semantic descriptor that
controls its placement is selected by the generic callosal-separator learner.
Connectedness is not assumed: all cells of a learned color may form one
pattern object inside their common bounding box.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .callosal_separator import SemanticObservation, SeparatorModel, learn_minimal_separator
from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color


def _color_cells(grid: Grid, color: int) -> set[tuple[int, int]]:
    return {
        (row, column)
        for row, values in enumerate(grid)
        for column, value in enumerate(values)
        if value == color
    }


def _bbox(cells: set[tuple[int, int]]) -> tuple[int, int, int, int]:
    rows = [row for row, _ in cells]
    columns = [column for _, column in cells]
    return min(rows), min(columns), max(rows), max(columns)


def _top_asymmetry_side(cells: set[tuple[int, int]]) -> Optional[str]:
    if not cells:
        return None
    row0, column0, _, column1 = _bbox(cells)
    top_columns = sorted(column for row, column in cells if row == row0)
    if not top_columns:
        return None
    center = (column0 + column1) / 2.0
    mean_column = sum(top_columns) / len(top_columns)
    if mean_column < center:
        return "left"
    if mean_column > center:
        return "right"
    return None


def _mirrored_cells(cells: set[tuple[int, int]], placement_side: str) -> set[tuple[int, int]]:
    _, column0, _, column1 = _bbox(cells)
    width = column1 - column0 + 1
    offset = -width if placement_side == "left" else width
    return {
        (row, column0 + (column1 - column) + offset)
        for row, column in cells
    }


def _bridge_descriptors(source_color: int, controller_color: int, controller_cells) -> dict[str, object]:
    row0, column0, row1, column1 = _bbox(controller_cells)
    return {
        "source_color": source_color,
        "controller_color": controller_color,
        "controller_orientation": _top_asymmetry_side(controller_cells),
        "controller_height": row1 - row0 + 1,
        "controller_width": column1 - column0 + 1,
        "controller_area": len(controller_cells),
    }


@dataclass(frozen=True)
class ControllerOrientationMirrorCopy:
    """A discovered controller-object separator chooses mirror-copy placement."""

    source_color: int
    controller_color: int
    separator: SeparatorModel
    name: str = "controller_orientation_mirror_copy"
    description_length: int = 6

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "(source_object,controller_descriptors)<->mirror_copy_placement",
            "source_color": self.source_color,
            "controller_color": self.controller_color,
            "separator": self.separator.callosal_summary,
            "source_objecthood": "all source-color cells; connectedness not required",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        source = _color_cells(input_grid, self.source_color)
        controller = _color_cells(input_grid, self.controller_color)
        if not source or not controller:
            return tuple(tuple(None for _ in row) for row in input_grid)
        placement_side = self.separator.predict(
            _bridge_descriptors(self.source_color, self.controller_color, controller)
        )
        if placement_side not in {"left", "right"}:
            return tuple(tuple(None for _ in row) for row in input_grid)
        added = _mirrored_cells(source, str(placement_side))
        height = len(input_grid)
        width = len(input_grid[0])
        if any(not (0 <= row < height and 0 <= column < width) for row, column in added):
            return tuple(tuple(None for _ in row) for row in input_grid)
        output = [list(row) for row in input_grid]
        for row, column in added:
            output[row][column] = self.source_color
        return tuple(tuple(row) for row in output)


def _infer_one_pair(input_grid: Grid, output_grid: Grid):
    if len(input_grid) != len(output_grid) or len(input_grid[0]) != len(output_grid[0]):
        return None
    background = background_color(input_grid)
    changes = [
        (row, column, input_grid[row][column], output_grid[row][column])
        for row in range(len(input_grid))
        for column in range(len(input_grid[0]))
        if input_grid[row][column] != output_grid[row][column]
    ]
    if not changes or any(before != background for _, _, before, _ in changes):
        return None
    changed_colors = {after for _, _, _, after in changes}
    if len(changed_colors) != 1:
        return None
    source_color = next(iter(changed_colors))
    source = _color_cells(input_grid, source_color)
    if not source:
        return None
    nonbackground_colors = sorted(
        {color for row in input_grid for color in row if color != background}
    )
    controller_colors = [color for color in nonbackground_colors if color != source_color]
    if len(controller_colors) != 1:
        return None
    controller_color = controller_colors[0]
    controller = _color_cells(input_grid, controller_color)
    if not controller or _top_asymmetry_side(controller) is None:
        return None

    changed_cells = {(row, column) for row, column, _, _ in changes}
    if changed_cells == _mirrored_cells(source, "left"):
        placement = "left"
    elif changed_cells == _mirrored_cells(source, "right"):
        placement = "right"
    else:
        return None
    return source_color, controller_color, controller, placement


def propose_cross_object_bridge_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[ControllerOrientationMirrorCopy]:
    if enabled_operator_families is not None and "cross_object_bridge" not in enabled_operator_families:
        return []
    if not training_pairs:
        return []

    source_color: Optional[int] = None
    controller_color: Optional[int] = None
    observations: list[SemanticObservation] = []
    for input_grid, output_grid in training_pairs:
        inferred = _infer_one_pair(input_grid, output_grid)
        if inferred is None:
            return []
        source, controller, controller_cells, placement = inferred
        if source_color is None:
            source_color = source
            controller_color = controller
        elif source_color != source or controller_color != controller:
            return []
        observations.append(
            SemanticObservation(
                _bridge_descriptors(source, controller, controller_cells), placement
            )
        )

    if source_color is None or controller_color is None:
        return []
    separator = learn_minimal_separator(
        observations,
        (
            "source_color",
            "controller_color",
            "controller_orientation",
            "controller_height",
            "controller_width",
            "controller_area",
        ),
        max_arity=2,
    )
    if separator is None:
        return []

    candidate = ControllerOrientationMirrorCopy(source_color, controller_color, separator)
    if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
        return [candidate]
    return []
