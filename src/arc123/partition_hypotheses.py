"""Generic hypotheses over grids partitioned by uniform divider lines.

Two distinct grammars are intentionally kept separate:

1. ``PartitionCellLabeler`` tests the hypothesis that each compartment can be
   labeled independently from its own descriptors.  ARC task 09629e4f is a
   documented negative control for this hypothesis: identical local masks can
   require different labels.
2. ``PartitionKeyRouter`` selects one relationally distinguished compartment
   and interprets its *local coordinates* as a macro-grid routing map.  This is
   a generic control-object construction: partition -> key selection ->
   local-to-macro projection.

The second grammar was added only after the first was falsified and independent
post-hoc analyses of the already-open development task agreed on the sparse-key
structure. No task ID or held-out target is available to live inference.
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
        divider_color, _, _, row_segments, column_segments = parsed
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


def _uniform_partition_geometry(
    row_segments: Sequence[tuple[int, int]],
    column_segments: Sequence[tuple[int, int]],
) -> Optional[tuple[int, int]]:
    heights = {r1 - r0 for r0, r1 in row_segments}
    widths = {c1 - c0 for c0, c1 in column_segments}
    if len(heights) != 1 or len(widths) != 1:
        return None
    return next(iter(heights)), next(iter(widths))


def _key_indices(
    blocks: Sequence[tuple[tuple[int, ...], ...]],
    background: int,
    selector: str,
) -> list[int]:
    descriptors = [_block_descriptors(block, background) for block in blocks]
    if selector == "unique_min_nonbackground_count":
        values = [int(item["nonbackground_count"]) for item in descriptors]
    elif selector == "unique_min_distinct_nonbackground_count":
        values = [int(item["distinct_nonbackground_count"]) for item in descriptors]
    else:
        raise ValueError(f"unknown partition key selector: {selector}")
    minimum = min(values)
    indices = [index for index, value in enumerate(values) if value == minimum]
    return indices if len(indices) == 1 else []


@dataclass(frozen=True)
class PartitionKeyRouter:
    """Use one sparse control compartment as a local-to-macro routing map."""

    divider_color: int
    background_value: int
    key_selector: str
    name: str = "partition_key_block_routing"
    description_length: int = 7

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "relational_key_block -> local_coordinate/color -> macro_block_effect",
            "divider_color": self.divider_color,
            "background_value": self.background_value,
            "key_selector": self.key_selector,
            "forward_deterministic": True,
            "backward_semantics": "solid macro labels constrain the key block's local colored coordinates",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        parsed = _partition(input_grid)
        if parsed is None:
            return tuple(tuple(None for _ in row) for row in input_grid)
        divider, row_dividers, column_dividers, row_segments, column_segments = parsed
        if divider != self.divider_color:
            return tuple(tuple(None for _ in row) for row in input_grid)
        geometry = _uniform_partition_geometry(row_segments, column_segments)
        if geometry is None:
            return tuple(tuple(None for _ in row) for row in input_grid)
        block_height, block_width = geometry
        # Local key coordinates must address the macro grid exactly.
        if block_height != len(row_segments) or block_width != len(column_segments):
            return tuple(tuple(None for _ in row) for row in input_grid)

        blocks = [
            _block_values(input_grid, rows, columns)
            for rows in row_segments
            for columns in column_segments
        ]
        key_indices = _key_indices(blocks, self.background_value, self.key_selector)
        if len(key_indices) != 1:
            return tuple(tuple(None for _ in row) for row in input_grid)
        key = blocks[key_indices[0]]

        output: list[list[Optional[int]]] = [
            [self.background_value for _ in row] for row in input_grid
        ]
        # Preserve divider rows/columns exactly.
        for row in row_dividers:
            output[row] = list(input_grid[row])
        for column in column_dividers:
            for row in range(len(input_grid)):
                output[row][column] = input_grid[row][column]

        for local_row, values in enumerate(key):
            for local_column, color in enumerate(values):
                if color == self.background_value:
                    continue
                rows = row_segments[local_row]
                columns = column_segments[local_column]
                r0, r1 = rows
                c0, c1 = columns
                for row in range(r0, r1):
                    for column in range(c0, c1):
                        output[row][column] = color
        return tuple(tuple(row) for row in output)


def _propose_independent_cell_labeler(
    training_pairs: Sequence[TrainingPair],
) -> list[PartitionCellLabeler]:
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
        max_arity=3,
    )
    if separator is None:
        return []
    candidate = PartitionCellLabeler(divider_color, background_value, separator)
    if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
        return [candidate]
    return []


def _propose_key_routers(training_pairs: Sequence[TrainingPair]) -> list[PartitionKeyRouter]:
    if not training_pairs:
        return []
    first = _partition(training_pairs[0][0])
    if first is None:
        return []
    divider, row_dividers, column_dividers, _, _ = first
    background = _nondivider_background(training_pairs[0][0], row_dividers, column_dividers, divider)
    if background is None:
        return []

    candidates = [
        PartitionKeyRouter(divider, background, "unique_min_nonbackground_count"),
        PartitionKeyRouter(divider, background, "unique_min_distinct_nonbackground_count"),
    ]
    return [
        candidate
        for candidate in candidates
        if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs)
    ]


def propose_partition_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
):
    if not training_pairs:
        return []
    enabled = None if enabled_operator_families is None else set(enabled_operator_families)
    candidates = []
    if enabled is None or "partition_cell_semantic_label" in enabled:
        candidates.extend(_propose_independent_cell_labeler(training_pairs))
    if enabled is None or "partition_key_block_routing" in enabled:
        candidates.extend(_propose_key_routers(training_pairs))
    return candidates
