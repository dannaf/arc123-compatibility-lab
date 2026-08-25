"""Generic divider-partition semantic labeling.

Detect a grid partitioned by full uniform divider rows/columns, treat each
rectangular compartment as a semantic unit, derive generic descriptors, and
learn a minimal descriptor->constant-output-label separator.  This supports
ARC tasks where local colors are distractors but occupancy/shape is the true
callosal state.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional, Sequence

from .callosal_separator import SemanticObservation, SeparatorModel, learn_minimal_separator
from .model import Grid, PartialGrid, TrainingPair


def _full_uniform_rows(grid: Grid) -> list[tuple[int, int]]:
    return [
        (row_index, row[0])
        for row_index, row in enumerate(grid)
        if row and all(value == row[0] for value in row)
    ]


def _full_uniform_columns(grid: Grid) -> list[tuple[int, int]]:
    height = len(grid)
    width = len(grid[0])
    result = []
    for column in range(width):
        value = grid[0][column]
        if all(grid[row][column] == value for row in range(height)):
            result.append((column, value))
    return result


def _segments(length: int, dividers: Sequence[int]) -> tuple[tuple[int, int], ...]:
    cuts = [-1, *sorted(dividers), length]
    return tuple(
        (left + 1, right)
        for left, right in zip(cuts, cuts[1:])
        if right - left > 1
    )


def _partition(grid: Grid):
    rows = _full_uniform_rows(grid)
    columns = _full_uniform_columns(grid)
    if not rows or not columns:
        return None
    common = set(value for _, value in rows) & set(value for _, value in columns)
    for divider_color in sorted(common):
        row_dividers = [index for index, value in rows if value == divider_color]
        column_dividers = [index for index, value in columns if value == divider_color]
        row_segments = _segments(len(grid), row_dividers)
        column_segments = _segments(len(grid[0]), column_dividers)
        if len(row_segments) >= 2 and len(column_segments) >= 2:
            return divider_color, tuple(row_dividers), tuple(column_dividers), row_segments, column_segments
    return None


def _nondivider_background(
    grid: Grid,
    row_dividers: Sequence[int],
    column_dividers: Sequence[int],
    divider_color: int,
) -> Optional[int]:
    counts = Counter(
        grid[row][column]
        for row in range(len(grid))
        for column in range(len(grid[0]))
        if row not in row_dividers
        and column not in column_dividers
        and grid[row][column] != divider_color
    )
    if not counts:
        return None
    best = max(counts.values())
    winners = [value for value, count in counts.items() if count == best]
    return min(winners) if winners else None


def _block_values(grid: Grid, rows: tuple[int, int], columns: tuple[int, int]) -> tuple[tuple[int, ...], ...]:
    r0, r1 = rows
    c0, c1 = columns
    return tuple(tuple(grid[row][c0:c1]) for row in range(r0, r1))


def _block_descriptors(block: tuple[tuple[int, ...], ...], background: int) -> dict[str, object]:
    height = len(block)
    width = len(block[0])
    occupancy = tuple(
        tuple(int(value != background) for value in row)
        for row in block
    )
    flat = [value for row in block for value in row]
    nonbackground = [value for value in flat if value != background]
    return {
        "height": height,
        "width": width,
        "area": height * width,
        "nonbackground_count": len(nonbackground),
        "occupancy_mask": occupancy,
        "distinct_nonbackground_count": len(set(nonbackground)),
        "sorted_nonbackground_values": tuple(sorted(nonbackground)),
    }


@dataclass(frozen=True)
class PartitionCellLabeler:
    divider_color: int
    background_value: int
    separator: SeparatorModel
    name: str = "partition_cell_semantic_label"
    description_length: int = 6

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "partition_cell_descriptors<->constant_output_label",
            "divider_color": self.divider_color,
            "background_value": self.background_value,
            "separator": self.separator.callosal_summary,
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        parsed = _partition(input_grid)
        if parsed is None:
            return tuple(tuple(None for _ in row) for row in input_grid)
        divider_color, row_dividers, column_dividers, row_segments, column_segments = parsed
        if divider_color != self.divider_color:
            return tuple(tuple(None for _ in row) for row in input_grid)
        output: list[list[Optional[int]]] = [list(row) for row in input_grid]
        for rows in row_segments:
            for columns in column_segments:
                block = _block_values(input_grid, rows, columns)
                label = self.separator.predict(_block_descriptors(block, self.background_value))
                r0, r1 = rows
                c0, c1 = columns
                for row in range(r0, r1):
                    for column in range(c0, c1):
                        output[row][column] = label
        return tuple(tuple(row) for row in output)


def propose_partition_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[PartitionCellLabeler]:
    if enabled_operator_families is not None and "partition_cell_semantic_label" not in enabled_operator_families:
        return []
    if not training_pairs:
        return []

    divider_color: Optional[int] = None
    background_value: Optional[int] = None
    observations: list[SemanticObservation] = []

    for input_grid, output_grid in training_pairs:
        if len(input_grid) != len(output_grid) or len(input_grid[0]) != len(output_grid[0]):
            return []
        parsed = _partition(input_grid)
        if parsed is None:
            return []
        divider, row_dividers, column_dividers, row_segments, column_segments = parsed
        if divider_color is None:
            divider_color = divider
        elif divider_color != divider:
            return []
        background = _nondivider_background(input_grid, row_dividers, column_dividers, divider)
        if background is None:
            return []
        if background_value is None:
            background_value = background
        elif background_value != background:
            return []

        # Divider structure must be preserved exactly.
        for row in row_dividers:
            if tuple(output_grid[row]) != tuple(input_grid[row]):
                return []
        for column in column_dividers:
            if any(output_grid[row][column] != input_grid[row][column] for row in range(len(input_grid))):
                return []

        for rows in row_segments:
            for columns in column_segments:
                input_block = _block_values(input_grid, rows, columns)
                output_block = _block_values(output_grid, rows, columns)
                labels = {value for row in output_block for value in row}
                if len(labels) != 1:
                    return []
                observations.append(
                    SemanticObservation(_block_descriptors(input_block, background), next(iter(labels)))
                )

    if divider_color is None or background_value is None:
        return []
    separator = learn_minimal_separator(
        observations,
        (
            "height",
            "width",
            "area",
            "nonbackground_count",
            "occupancy_mask",
            "distinct_nonbackground_count",
            "sorted_nonbackground_values",
        ),
        max_arity=2,
    )
    if separator is None:
        return []
    candidate = PartitionCellLabeler(divider_color, background_value, separator)
    if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
        return [candidate]
    return []
