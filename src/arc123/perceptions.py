"""Generic grid perceptions used by the first non-VLM ARC123 controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .model import Grid


@dataclass(frozen=True)
class Component:
    color: int
    cells: tuple[tuple[int, int], ...]
    bbox: tuple[int, int, int, int]

    @property
    def area(self) -> int:
        return len(self.cells)


def background_color(grid: Grid) -> int:
    counts: dict[int, int] = {}
    for row in grid:
        for color in row:
            counts[color] = counts.get(color, 0) + 1
    return min(counts, key=lambda color: (-counts[color], color))


def color_inventory(grids: Sequence[Grid]) -> tuple[int, ...]:
    return tuple(sorted({color for grid in grids for row in grid for color in row}))


def connected_components(
    grid: Grid, connectivity: int = 4, include_background: bool = False
) -> tuple[Component, ...]:
    if connectivity not in {4, 8}:
        raise ValueError("connectivity must be 4 or 8")
    background = background_color(grid)
    offsets = [(-1, 0), (0, -1), (0, 1), (1, 0)]
    if connectivity == 8:
        offsets.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
    visited: set[tuple[int, int]] = set()
    components: list[Component] = []
    height = len(grid)
    width = len(grid[0])
    for row_index in range(height):
        for column_index in range(width):
            start = (row_index, column_index)
            color = grid[row_index][column_index]
            if start in visited or (not include_background and color == background):
                continue
            stack = [start]
            visited.add(start)
            cells: list[tuple[int, int]] = []
            while stack:
                row, column = stack.pop()
                cells.append((row, column))
                for row_offset, column_offset in offsets:
                    neighbor = (row + row_offset, column + column_offset)
                    if (
                        neighbor[0] < 0
                        or neighbor[0] >= height
                        or neighbor[1] < 0
                        or neighbor[1] >= width
                        or neighbor in visited
                        or grid[neighbor[0]][neighbor[1]] != color
                    ):
                        continue
                    visited.add(neighbor)
                    stack.append(neighbor)
            ordered = tuple(sorted(cells))
            rows = [cell[0] for cell in ordered]
            columns = [cell[1] for cell in ordered]
            components.append(
                Component(color, ordered, (min(rows), min(columns), max(rows), max(columns)))
            )
    return tuple(sorted(components, key=lambda item: (item.bbox, item.color, item.area)))


def changed_cell_count(input_grid: Grid, output_grid: Grid) -> int:
    if len(input_grid) != len(output_grid) or len(input_grid[0]) != len(output_grid[0]):
        return len(output_grid) * len(output_grid[0])
    return sum(
        input_color != output_color
        for input_row, output_row in zip(input_grid, output_grid)
        for input_color, output_color in zip(input_row, output_row)
    )


def difference_summary(input_grid: Grid, output_grid: Grid) -> dict[str, int | bool]:
    input_height, input_width = len(input_grid), len(input_grid[0])
    output_height, output_width = len(output_grid), len(output_grid[0])
    return {
        "input_height": input_height,
        "input_width": input_width,
        "output_height": output_height,
        "output_width": output_width,
        "shape_changed": (input_height, input_width) != (output_height, output_width),
        "changed_cell_count": changed_cell_count(input_grid, output_grid),
    }
