"""Cross-object bridge hypotheses for relational ARC transformations.

The first family learns when one object's small orientation descriptor controls
where a transformed copy of another object is placed. All colors, bridge
states, and mapping parameters are inferred from visible training evidence.

Important representation guardrail: a semantic object need not be one
4-neighbor connected component. For this family, all cells of a learned color
inside their bounding box form the pattern object; this is required by ARC2
`760b3cac`, where the controlled upper pattern can be disconnected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

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
    row0, column0, _, column1 = _bbox(cells)
    width = column1 - column0 + 1
    offset = -width if placement_side == "left" else width
    return {
        (row, column0 + (column1 - column) + offset)
        for row, column in cells
    }


@dataclass(frozen=True)
class ControllerOrientationMirrorCopy:
    """A controller object's asymmetry chooses left/right placement of a mirrored source copy."""

    source_color: int
    controller_color: int
    bridge_mapping: tuple[tuple[str, str], ...]
    name: str = "controller_orientation_mirror_copy"
    description_length: int = 6

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "(source_color_pattern, controller_orientation)->mirrored_copy_placement",
            "source_color": self.source_color,
            "controller_color": self.controller_color,
            "bridge_mapping": self.bridge_mapping,
            "source_objecthood": "all cells of source color in their bounding box; connectedness not required",
            "forward_deterministic": True,
            "backward_semantics": "observed placement eliminates incompatible controller orientations",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        source = _color_cells(input_grid, self.source_color)
        controller = _color_cells(input_grid, self.controller_color)
        if not source or not controller:
            return tuple(tuple(None for _ in row) for row in input_grid)
        bridge_state = _top_asymmetry_side(controller)
        mapping = dict(self.bridge_mapping)
        if bridge_state is None or bridge_state not in mapping:
            return tuple(tuple(None for _ in row) for row in input_grid)
        placement_side = mapping[bridge_state]
        added = _mirrored_cells(source, placement_side)
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
    if not changes:
        return None
    # This family is additive: all changed cells were background and become one source color.
    if any(before != background for _, _, before, _ in changes):
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
    if not controller:
        return None
    bridge_state = _top_asymmetry_side(controller)
    if bridge_state is None:
        return None

    changed_cells = {(row, column) for row, column, _, _ in changes}
    left_cells = _mirrored_cells(source, "left")
    right_cells = _mirrored_cells(source, "right")
    if changed_cells == left_cells:
        placement = "left"
    elif changed_cells == right_cells:
        placement = "right"
    else:
        return None
    return source_color, controller_color, bridge_state, placement


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
    mapping: dict[str, str] = {}
    for input_grid, output_grid in training_pairs:
        inferred = _infer_one_pair(input_grid, output_grid)
        if inferred is None:
            return []
        source, controller, state, placement = inferred
        if source_color is None:
            source_color = source
            controller_color = controller
        elif source_color != source or controller_color != controller:
            return []
        prior = mapping.get(state)
        if prior is not None and prior != placement:
            return []
        mapping[state] = placement
    if source_color is None or controller_color is None or not mapping:
        return []
    candidate = ControllerOrientationMirrorCopy(
        source_color=source_color,
        controller_color=controller_color,
        bridge_mapping=tuple(sorted(mapping.items())),
    )
    if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
        return [candidate]
    return []
