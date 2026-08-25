"""Generic grammars where a compact control signal parameterizes a remote transform.

These hypotheses deliberately expose a common callosal pattern:

    small controller / marker structure -> semantic parameter -> remote effect

No task identifiers or held-out targets participate in inference.  A production
is proposed only when the same structural rule exactly explains every visible
training pair; unsupported test structures remain UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color, connected_components


def _is_rectangular_frame(component) -> bool:
    row0, column0, row1, column1 = component.bbox
    if row1 - row0 + 1 < 4 or column1 - column0 + 1 < 4:
        return False
    perimeter = {
        (row, column)
        for row in range(row0, row1 + 1)
        for column in range(column0, column1 + 1)
        if row in {row0, row1} or column in {column0, column1}
    }
    return set(component.cells) == perimeter


def _unique_frame(grid: Grid):
    frames = tuple(component for component in connected_components(grid) if _is_rectangular_frame(component))
    return frames[0] if len(frames) == 1 else None


def _corner_for_cell(row: int, column: int, bbox: tuple[int, int, int, int]) -> Optional[tuple[int, int]]:
    row0, column0, row1, column1 = bbox
    if row < row0:
        vertical = 0
    elif row > row1:
        vertical = 1
    else:
        return None
    if column < column0:
        horizontal = 0
    elif column > column1:
        horizontal = 1
    else:
        return None
    return vertical, horizontal


def _external_corner_markers(grid: Grid, frame) -> Optional[tuple[tuple[int, int, int], ...]]:
    background = background_color(grid)
    frame_cells = set(frame.cells)
    markers: list[tuple[int, int, int]] = []
    for row in range(len(grid)):
        for column in range(len(grid[0])):
            value = grid[row][column]
            if value == background or (row, column) in frame_cells:
                continue
            if value == frame.color:
                return None
            if _corner_for_cell(row, column, frame.bbox) is None:
                return None
            markers.append((row, column, value))
    if len(markers) != 2 or len({value for _, _, value in markers}) != 2:
        return None
    corners = [_corner_for_cell(row, column, frame.bbox) for row, column, _ in markers]
    if corners[0] == corners[1]:
        return None
    # Opposite corner markers would demand conflicting colors on the same two
    # diagonal quadrants.  Adjacent corner markers induce a complete partition.
    if corners[0] == (1 - corners[1][0], 1 - corners[1][1]):
        return None
    return tuple(markers)


@dataclass(frozen=True)
class CornerMarkerDiagonalQuadrantFill:
    """Fill a frame's quadrant nearest each marker and the opposite quadrant."""

    name: str = "corner_marker_diagonal_quadrant_fill"
    description_length: int = 6

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "external_corner_marker -> nearest_and_opposite_interior_quadrants",
            "parameter": "marker corner class and marker color",
            "forward_deterministic": True,
            "backward_semantics": "filled diagonal pair identifies the external marker corner class",
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        frame = _unique_frame(input_grid)
        if frame is None:
            return None
        row0, column0, row1, column1 = frame.bbox
        interior_height = row1 - row0 - 1
        interior_width = column1 - column0 - 1
        if interior_height <= 0 or interior_width <= 0 or interior_height % 2 or interior_width % 2:
            return None
        markers = _external_corner_markers(input_grid, frame)
        if markers is None:
            return None
        background = background_color(input_grid)
        output = [list(row) for row in input_grid]
        mid_row = row0 + interior_height // 2
        mid_column = column0 + interior_width // 2
        for marker_row, marker_column, marker_color in markers:
            corner = _corner_for_cell(marker_row, marker_column, frame.bbox)
            if corner is None:
                return None
            target_quadrants = {corner, (1 - corner[0], 1 - corner[1])}
            for row in range(row0 + 1, row1):
                vertical = 0 if row <= mid_row else 1
                for column in range(column0 + 1, column1):
                    horizontal = 0 if column <= mid_column else 1
                    if (vertical, horizontal) not in target_quadrants:
                        continue
                    if input_grid[row][column] != background:
                        return None
                    output[row][column] = marker_color
        return tuple(tuple(row) for row in output)


def _terminal_palette_and_controller(
    grid: Grid,
) -> Optional[tuple[int, tuple[int, ...], int, int]]:
    """Return palette_start, palette colors, controller column, controller count."""

    background = background_color(grid)
    height = len(grid)
    width = len(grid[0])
    palette_colors_reversed: list[int] = []
    column = width - 1
    while column >= 0:
        values = {grid[row][column] for row in range(height)}
        if len(values) != 1:
            break
        value = next(iter(values))
        if value == background:
            break
        palette_colors_reversed.append(value)
        column -= 1
    if len(palette_colors_reversed) < 2:
        return None
    palette_start = column + 1
    if palette_start < 1:
        return None
    palette_colors = tuple(reversed(palette_colors_reversed))
    if len(set(palette_colors)) != len(palette_colors):
        return None

    outside_nonbackground = [
        (row, col, grid[row][col])
        for row in range(height)
        for col in range(palette_start)
        if grid[row][col] != background
    ]
    if not outside_nonbackground:
        return None
    controller_columns = {col for _, col, _ in outside_nonbackground}
    controller_colors = {value for _, _, value in outside_nonbackground}
    if len(controller_columns) != 1 or len(controller_colors) != 1:
        return None
    controller_column = next(iter(controller_columns))
    controller_count = len(outside_nonbackground)
    if controller_count >= height:
        return None
    target_column = palette_start - 1
    if controller_column == target_column:
        return None
    if any(grid[row][target_column] != background for row in range(height)):
        return None
    return palette_start, palette_colors, controller_column, controller_count


@dataclass(frozen=True)
class MarkerCountPaletteCycle:
    """Use controller cardinality as run length for a repeated palette sequence."""

    name: str = "marker_count_palette_cycle"
    description_length: int = 6

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "controller_cardinality -> palette_run_length",
            "controller": "single-color nonterminal marker column",
            "payload": "terminal constant-color palette columns",
            "effect": "cyclic vertical sequence in column immediately before palette",
            "forward_deterministic": True,
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        parsed = _terminal_palette_and_controller(input_grid)
        if parsed is None:
            return None
        palette_start, palette_colors, _, run_length = parsed
        background = background_color(input_grid)
        height = len(input_grid)
        width = len(input_grid[0])
        output = [list(row) for row in input_grid]
        for row in range(height):
            for column in range(palette_start, width):
                output[row][column] = background
        target_column = palette_start - 1
        for row in range(height):
            output[row][target_column] = palette_colors[(row // run_length) % len(palette_colors)]
        return tuple(tuple(row) for row in output)


def propose_control_parameter_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[object]:
    if not training_pairs:
        return []
    enabled = set(enabled_operator_families or ())
    use_all = enabled_operator_families is None
    candidates: list[object] = []

    if use_all or "corner_marker_diagonal_quadrant_fill" in enabled:
        candidate = CornerMarkerDiagonalQuadrantFill()
        if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
            candidates.append(candidate)

    if use_all or "marker_count_palette_cycle" in enabled:
        candidate = MarkerCountPaletteCycle()
        if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
            candidates.append(candidate)

    return candidates
