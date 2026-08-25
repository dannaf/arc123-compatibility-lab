"""Generic straight-segment relational grammars.

The structural operation (equalize directed straight segments) is separated
from the integer expression that chooses the common length.  This prevents a
single training-exact statistic from masquerading as semantic singularity when
other equally simple parameterizations fit the demonstrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .parameter_expressions import (
    IntegerSequenceExpression,
    compatible_integer_sequence_expression_fiber,
)
from .perceptions import background_color


Cell = tuple[int, int]
Segment = tuple[int, tuple[Cell, ...], str]


def _eight_connected_components(grid: Grid) -> list[tuple[int, tuple[Cell, ...]]]:
    background = background_color(grid)
    height, width = len(grid), len(grid[0])
    unseen = {
        (r, c)
        for r in range(height)
        for c in range(width)
        if grid[r][c] != background
    }
    components: list[tuple[int, tuple[Cell, ...]]] = []
    while unseen:
        seed = min(unseen)
        color = grid[seed[0]][seed[1]]
        stack = [seed]
        unseen.remove(seed)
        cells: set[Cell] = {seed}
        while stack:
            r, c = stack.pop()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if not (dr or dc):
                        continue
                    nxt = (r + dr, c + dc)
                    if nxt in unseen and grid[nxt[0]][nxt[1]] == color:
                        unseen.remove(nxt)
                        cells.add(nxt)
                        stack.append(nxt)
        components.append((color, tuple(sorted(cells))))
    return components


def _straight_orientation(cells: tuple[Cell, ...]) -> Optional[str]:
    if not cells:
        return None
    rows = {r for r, _ in cells}
    cols = {c for _, c in cells}
    if len(rows) == 1:
        lo, hi = min(cols), max(cols)
        return "horizontal" if len(cells) == hi - lo + 1 else None
    if len(cols) == 1:
        lo, hi = min(rows), max(rows)
        return "vertical" if len(cells) == hi - lo + 1 else None
    diffs = {r - c for r, c in cells}
    if len(diffs) == 1:
        ordered = sorted(cells)
        return "main_diagonal" if all(
            ordered[i + 1][0] - ordered[i][0] == 1
            and ordered[i + 1][1] - ordered[i][1] == 1
            for i in range(len(ordered) - 1)
        ) else None
    sums = {r + c for r, c in cells}
    if len(sums) == 1:
        ordered = sorted(cells)
        return "anti_diagonal" if all(
            ordered[i + 1][0] - ordered[i][0] == 1
            and ordered[i][1] - ordered[i + 1][1] == 1
            for i in range(len(ordered) - 1)
        ) else None
    return None


def _segments(grid: Grid) -> Optional[tuple[Segment, ...]]:
    components = _eight_connected_components(grid)
    if len(components) < 2:
        return None
    result: list[Segment] = []
    for color, cells in components:
        orientation = _straight_orientation(cells)
        if orientation is None:
            return None
        result.append((color, cells, orientation))
    orientations = {orientation for _, _, orientation in result}
    if len(orientations) != 1:
        return None
    return tuple(result)


def _anchor_and_step(cells: tuple[Cell, ...], orientation: str) -> tuple[Cell, Cell]:
    if orientation == "horizontal":
        return min(cells, key=lambda cell: cell[1]), (0, 1)
    if orientation == "vertical":
        return min(cells, key=lambda cell: cell[0]), (1, 0)
    if orientation == "main_diagonal":
        return min(cells), (1, 1)
    if orientation == "anti_diagonal":
        return max(cells, key=lambda cell: (cell[0], -cell[1])), (-1, 1)
    raise ValueError(orientation)


def _render_equalized(input_grid: Grid, target: int) -> Optional[PartialGrid]:
    segments = _segments(input_grid)
    if segments is None or target < 1:
        return None
    background = background_color(input_grid)
    height, width = len(input_grid), len(input_grid[0])
    output = [[background for _ in range(width)] for _ in range(height)]
    claimed: dict[Cell, int] = {}
    for color, cells, orientation in segments:
        anchor, step = _anchor_and_step(cells, orientation)
        for offset in range(target):
            cell = (anchor[0] + step[0] * offset, anchor[1] + step[1] * offset)
            if not (0 <= cell[0] < height and 0 <= cell[1] < width):
                return None
            prior = claimed.get(cell)
            if prior is not None and prior != color:
                return None
            claimed[cell] = color
    for (r, c), color in claimed.items():
        output[r][c] = color
    return tuple(tuple(row) for row in output)


@dataclass(frozen=True)
class SegmentStatisticEqualize:
    statistic: IntegerSequenceExpression
    description_length: int = 6

    @property
    def name(self) -> str:
        return f"segment_statistic_equalize[{self.statistic.name}]"

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "segment_length_sequence -> target_extent -> each_segment_extent",
            "parameter_expression": self.statistic.name,
            "parameter_expression_cost": self.statistic.cost,
            "orientations": ("horizontal", "vertical", "main_diagonal", "anti_diagonal"),
            "canonical_anchors": {
                "horizontal": "left",
                "vertical": "top",
                "main_diagonal": "top_left",
                "anti_diagonal": "bottom_left",
            },
            "forward_deterministic_given_parameter": True,
            "parameter_fiber_preserved": True,
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        segments = _segments(input_grid)
        if segments is None:
            return None
        target = self.statistic.evaluate([len(cells) for _, cells, _ in segments])
        if target is None:
            return None
        return _render_equalized(input_grid, target)


@dataclass(frozen=True)
class SecondLongestSegmentEqualize:
    """Legacy explicit parameterization retained for historical packet replay."""

    name: str = "second_longest_segment_equalize"
    description_length: int = 6

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "global_segment_length_order_statistic -> each_segment_extent",
            "target_length": "second_longest_input_segment_length",
            "legacy_fixed_parameterization": True,
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        segments = _segments(input_grid)
        if segments is None:
            return None
        lengths = sorted((len(cells) for _, cells, _ in segments), reverse=True)
        if len(lengths) < 2:
            return None
        return _render_equalized(input_grid, lengths[1])


def _training_target_observations(
    training_pairs: Sequence[TrainingPair],
) -> Optional[tuple[tuple[tuple[int, ...], int], ...]]:
    observations: list[tuple[tuple[int, ...], int]] = []
    for input_grid, output_grid in training_pairs:
        input_segments = _segments(input_grid)
        output_segments = _segments(output_grid)
        if input_segments is None or output_segments is None:
            return None
        output_lengths = {len(cells) for _, cells, _ in output_segments}
        if len(output_lengths) != 1:
            return None
        target = next(iter(output_lengths))
        observations.append((tuple(len(cells) for _, cells, _ in input_segments), target))
    return tuple(observations)


def propose_segment_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[SegmentStatisticEqualize | SecondLongestSegmentEqualize]:
    if not training_pairs:
        return []
    enabled = set(enabled_operator_families or ()) if enabled_operator_families is not None else None
    candidates: list[SegmentStatisticEqualize | SecondLongestSegmentEqualize] = []

    if enabled is None or "segment_statistic_equalize" in enabled:
        observations = _training_target_observations(training_pairs)
        if observations is not None:
            fiber = compatible_integer_sequence_expression_fiber(observations)
            candidates.extend(SegmentStatisticEqualize(expression) for expression in fiber)

    # Keep the old named rule solely so historical packets that explicitly
    # request it remain reproducible. New default operation uses the fiber.
    if enabled is None or "second_longest_segment_equalize" in enabled:
        candidate = SecondLongestSegmentEqualize()
        if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
            candidates.append(candidate)

    return [
        candidate
        for candidate in candidates
        if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs)
    ]
