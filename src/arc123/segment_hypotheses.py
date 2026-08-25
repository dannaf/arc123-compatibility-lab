"""Generic straight-segment relational grammars."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
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


@dataclass(frozen=True)
class SecondLongestSegmentEqualize:
    """Equalize directed straight segments to the second-longest input length."""

    name: str = "second_longest_segment_equalize"
    description_length: int = 6

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "global_segment_length_order_statistic -> each_segment_extent",
            "target_length": "second_longest_input_segment_length",
            "orientations": ("horizontal", "vertical", "main_diagonal", "anti_diagonal"),
            "canonical_anchors": {
                "horizontal": "left",
                "vertical": "top",
                "main_diagonal": "top_left",
                "anti_diagonal": "bottom_left",
            },
            "forward_deterministic": True,
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        segments = _segments(input_grid)
        if segments is None:
            return None
        lengths = sorted((len(cells) for _, cells, _ in segments), reverse=True)
        if len(lengths) < 2:
            return None
        target = lengths[1]
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


def propose_segment_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[SecondLongestSegmentEqualize]:
    if enabled_operator_families is not None and (
        "second_longest_segment_equalize" not in enabled_operator_families
    ):
        return []
    if not training_pairs:
        return []
    candidate = SecondLongestSegmentEqualize()
    return [candidate] if all(
        candidate.predict(input_grid) == output_grid
        for input_grid, output_grid in training_pairs
    ) else []
