"""Generic semantic-interface hypotheses for ARC123.

These operators are deliberately task-ID agnostic.  They are proposed only from
visible training input/output structure and preserve UNKNOWN on unsupported
semantic keys.  They are the first implementation of issue #10's semantic
callosal refinement ladder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color


def _same_shape(training_pairs: Sequence[TrainingPair]) -> bool:
    return all(
        len(input_grid) == len(output_grid)
        and len(input_grid[0]) == len(output_grid[0])
        for input_grid, output_grid in training_pairs
    )


@dataclass(frozen=True)
class RowMarkerColumnMap:
    """Map a row's unique non-background marker column to a constant output row.

    This is a semantic corpus-callosum quotient: the whole input row is reduced
    to the marker's column.  A test row using an unseen column remains UNKNOWN.
    """

    mapping: tuple[tuple[int, int], ...]
    name: str = "row_marker_column_to_constant_row"
    description_length: int = 4

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        background = background_color(input_grid)
        learned = dict(self.mapping)
        width = len(input_grid[0])
        rows: list[tuple[Optional[int], ...]] = []
        for row in input_grid:
            markers = [index for index, color in enumerate(row) if color != background]
            if len(markers) != 1 or markers[0] not in learned:
                rows.append(tuple(None for _ in range(width)))
                continue
            output_color = learned[markers[0]]
            rows.append(tuple(output_color for _ in range(width)))
        return tuple(rows)


@dataclass(frozen=True)
class ColumnDownwardPropagation:
    """Propagate the most recent non-background marker down each column."""

    name: str = "column_downward_propagation"
    description_length: int = 3

    def predict(self, input_grid: Grid) -> PartialGrid:
        background = background_color(input_grid)
        height = len(input_grid)
        width = len(input_grid[0])
        output = [[background for _ in range(width)] for _ in range(height)]
        for column in range(width):
            active = background
            for row in range(height):
                color = input_grid[row][column]
                if color != background:
                    active = color
                output[row][column] = active
        return tuple(tuple(row) for row in output)


@dataclass(frozen=True)
class EnclosedBackgroundFill:
    """Fill 4-neighbor-enclosed background regions with one learned color."""

    fill_color: int
    name: str = "enclosed_background_fill"
    description_length: int = 4

    def predict(self, input_grid: Grid) -> PartialGrid:
        background = background_color(input_grid)
        height = len(input_grid)
        width = len(input_grid[0])
        reachable: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = []
        for row in range(height):
            for column in (0, width - 1):
                if input_grid[row][column] == background:
                    stack.append((row, column))
        for column in range(width):
            for row in (0, height - 1):
                if input_grid[row][column] == background:
                    stack.append((row, column))
        while stack:
            row, column = stack.pop()
            if (row, column) in reachable:
                continue
            if input_grid[row][column] != background:
                continue
            reachable.add((row, column))
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = row + dr, column + dc
                if 0 <= nr < height and 0 <= nc < width and (nr, nc) not in reachable:
                    stack.append((nr, nc))
        output = [list(row) for row in input_grid]
        for row in range(height):
            for column in range(width):
                if input_grid[row][column] == background and (row, column) not in reachable:
                    output[row][column] = self.fill_color
        return tuple(tuple(row) for row in output)


def _propose_row_marker_map(training_pairs: Sequence[TrainingPair]) -> Optional[RowMarkerColumnMap]:
    if not training_pairs or not _same_shape(training_pairs):
        return None
    mapping: dict[int, int] = {}
    observed_columns: set[int] = set()
    for input_grid, output_grid in training_pairs:
        background = background_color(input_grid)
        for input_row, output_row in zip(input_grid, output_grid):
            markers = [index for index, color in enumerate(input_row) if color != background]
            if len(markers) != 1 or len(set(output_row)) != 1:
                return None
            column = markers[0]
            output_color = output_row[0]
            prior = mapping.get(column)
            if prior is not None and prior != output_color:
                return None
            mapping[column] = output_color
            observed_columns.add(column)
    if len(observed_columns) < 2:
        return None
    return RowMarkerColumnMap(tuple(sorted(mapping.items())))


def _propose_enclosed_fill(training_pairs: Sequence[TrainingPair]) -> Optional[EnclosedBackgroundFill]:
    if not training_pairs or not _same_shape(training_pairs):
        return None
    fill_color: Optional[int] = None
    saw_change = False
    for input_grid, output_grid in training_pairs:
        background = background_color(input_grid)
        changed: list[tuple[int, int, int]] = []
        for row in range(len(input_grid)):
            for column in range(len(input_grid[0])):
                if input_grid[row][column] == output_grid[row][column]:
                    continue
                if input_grid[row][column] != background:
                    return None
                changed.append((row, column, output_grid[row][column]))
        if not changed:
            continue
        saw_change = True
        colors = {color for _, _, color in changed}
        if len(colors) != 1:
            return None
        candidate_color = next(iter(colors))
        if candidate_color == background:
            return None
        if fill_color is None:
            fill_color = candidate_color
        elif fill_color != candidate_color:
            return None
        candidate = EnclosedBackgroundFill(candidate_color)
        if candidate.predict(input_grid) != output_grid:
            return None
    if not saw_change or fill_color is None:
        return None
    return EnclosedBackgroundFill(fill_color)


def propose_semantic_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[object]:
    """Propose compact semantic interfaces after lower-level relations fail.

    The proposal order is intentionally simple-to-complex and all learned
    parameters come only from visible training pairs.
    """

    if enabled_operator_families is None:
        enabled = frozenset(
            {
                "row_marker_column_to_constant_row",
                "column_downward_propagation",
                "enclosed_background_fill",
            }
        )
    else:
        enabled = frozenset(enabled_operator_families)

    candidates: list[object] = []
    if "row_marker_column_to_constant_row" in enabled:
        row_marker = _propose_row_marker_map(training_pairs)
        if row_marker is not None:
            candidates.append(row_marker)
    if "column_downward_propagation" in enabled and _same_shape(training_pairs):
        candidates.append(ColumnDownwardPropagation())
    if "enclosed_background_fill" in enabled:
        enclosed = _propose_enclosed_fill(training_pairs)
        if enclosed is not None:
            candidates.append(enclosed)
    return candidates
