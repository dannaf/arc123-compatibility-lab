"""Generic, inspectable hypothesis operators for the first ARC123 learner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color, color_inventory


def _full(grid: Grid) -> PartialGrid:
    return tuple(tuple(color for color in row) for row in grid)


def _parameter_tuple(**parameters: int | str) -> tuple[tuple[str, int | str], ...]:
    return tuple(sorted(parameters.items()))


@dataclass(frozen=True)
class Hypothesis:
    """A generic partial program with explicit parameters and prediction scope."""

    kind: str
    parameters: tuple[tuple[str, int | str], ...] = ()
    description_length: int = 1

    @property
    def name(self) -> str:
        if not self.parameters:
            return self.kind
        parameters = ",".join(f"{key}={value}" for key, value in self.parameters)
        return f"{self.kind}({parameters})"

    @property
    def parameter_map(self) -> dict[str, int | str]:
        return dict(self.parameters)

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        if self.kind == "identity":
            return _full(input_grid)
        if self.kind == "recolor":
            return self._recolor(input_grid)
        if self.kind == "mirror":
            return self._mirror(input_grid)
        if self.kind == "translate":
            return self._translate(input_grid)
        if self.kind == "line_extend":
            return self._line_extend(input_grid)
        if self.kind == "row_span_fill":
            return self._row_span_fill(input_grid)
        raise ValueError(f"unknown generic hypothesis kind: {self.kind}")

    def _recolor(self, input_grid: Grid) -> PartialGrid:
        mapping = {
            int(key.removeprefix("from_")): int(value)
            for key, value in self.parameters
            if key.startswith("from_")
        }
        return tuple(
            tuple(mapping.get(color) for color in row)
            for row in input_grid
        )

    def _mirror(self, input_grid: Grid) -> PartialGrid:
        axis = self.parameter_map["axis"]
        if axis == "left_right":
            return tuple(tuple(reversed(row)) for row in input_grid)
        if axis == "top_bottom":
            return tuple(reversed(_full(input_grid)))
        if axis == "rotate_180":
            return tuple(tuple(reversed(row)) for row in reversed(input_grid))
        raise ValueError(f"unknown mirror axis: {axis}")

    def _translate(self, input_grid: Grid) -> PartialGrid:
        parameters = self.parameter_map
        row_offset = int(parameters["row_offset"])
        column_offset = int(parameters["column_offset"])
        background = background_color(input_grid)
        height = len(input_grid)
        width = len(input_grid[0])
        output = [[background for _ in range(width)] for _ in range(height)]
        for row_index, row in enumerate(input_grid):
            for column_index, color in enumerate(row):
                if color == background:
                    continue
                target_row = row_index + row_offset
                target_column = column_index + column_offset
                if 0 <= target_row < height and 0 <= target_column < width:
                    output[target_row][target_column] = color
        return tuple(tuple(row) for row in output)

    def _line_extend(self, input_grid: Grid) -> PartialGrid:
        parameters = self.parameter_map
        seed_color = int(parameters["seed_color"])
        fill_color = int(parameters["fill_color"])
        direction = str(parameters["direction"])
        offsets = {
            "up": (-1, 0),
            "down": (1, 0),
            "left": (0, -1),
            "right": (0, 1),
        }
        row_offset, column_offset = offsets[direction]
        background = background_color(input_grid)
        height = len(input_grid)
        width = len(input_grid[0])
        output = [list(row) for row in input_grid]
        seed_locations = [
            (row_index, column_index)
            for row_index, row in enumerate(input_grid)
            for column_index, color in enumerate(row)
            if color == seed_color
        ]
        for row_index, column_index in seed_locations:
            target_row = row_index + row_offset
            target_column = column_index + column_offset
            while 0 <= target_row < height and 0 <= target_column < width:
                if output[target_row][target_column] == background:
                    output[target_row][target_column] = fill_color
                target_row += row_offset
                target_column += column_offset
        return tuple(tuple(row) for row in output)

    def _row_span_fill(self, input_grid: Grid) -> PartialGrid:
        parameters = self.parameter_map
        seed_color = int(parameters["seed_color"])
        fill_color = int(parameters["fill_color"])
        background = background_color(input_grid)
        output = [list(row) for row in input_grid]
        for row_index, row in enumerate(input_grid):
            seed_columns = [
                column_index for column_index, color in enumerate(row) if color == seed_color
            ]
            if len(seed_columns) < 2:
                continue
            for column_index in range(min(seed_columns), max(seed_columns) + 1):
                if output[row_index][column_index] == background:
                    output[row_index][column_index] = fill_color
        return tuple(tuple(row) for row in output)


def _same_shape_training_pairs(training_pairs: Sequence[TrainingPair]) -> bool:
    return all(
        len(input_grid) == len(output_grid)
        and len(input_grid[0]) == len(output_grid[0])
        for input_grid, output_grid in training_pairs
    )


def _infer_recolor_mapping(
    training_pairs: Sequence[TrainingPair],
) -> Optional[tuple[tuple[str, int | str], ...]]:
    if not _same_shape_training_pairs(training_pairs):
        return None
    mapping: dict[int, int] = {}
    for input_grid, output_grid in training_pairs:
        for input_row, output_row in zip(input_grid, output_grid):
            for input_color, output_color in zip(input_row, output_row):
                prior = mapping.get(input_color)
                if prior is not None and prior != output_color:
                    return None
                mapping[input_color] = output_color
    return tuple(
        sorted((f"from_{input_color}", output_color) for input_color, output_color in mapping.items())
    )


def _translation_candidates(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    if not _same_shape_training_pairs(training_pairs):
        return []
    max_height = max(len(input_grid) for input_grid, _ in training_pairs)
    max_width = max(len(input_grid[0]) for input_grid, _ in training_pairs)
    candidates: list[Hypothesis] = []
    for row_offset in range(-max_height + 1, max_height):
        for column_offset in range(-max_width + 1, max_width):
            if row_offset == 0 and column_offset == 0:
                continue
            candidates.append(
                Hypothesis(
                    "translate",
                    _parameter_tuple(
                        row_offset=row_offset, column_offset=column_offset
                    ),
                    description_length=3,
                )
            )
    return candidates


def propose_base_hypotheses(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    """Propose generic global relations before inspecting structured residuals."""

    candidates = [Hypothesis("identity", description_length=1)]
    recolor_mapping = _infer_recolor_mapping(training_pairs)
    if recolor_mapping is not None:
        candidates.append(Hypothesis("recolor", recolor_mapping, description_length=2))
    if _same_shape_training_pairs(training_pairs):
        candidates.extend(
            [
                Hypothesis(
                    "mirror",
                    _parameter_tuple(axis="left_right"),
                    description_length=2,
                ),
                Hypothesis(
                    "mirror",
                    _parameter_tuple(axis="top_bottom"),
                    description_length=2,
                ),
                Hypothesis(
                    "mirror",
                    _parameter_tuple(axis="rotate_180"),
                    description_length=2,
                ),
            ]
        )
        candidates.extend(_translation_candidates(training_pairs))
    return candidates


def propose_structural_hypotheses(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    """Propose generic fill/extension relations only after residual-directed revision."""

    if not _same_shape_training_pairs(training_pairs):
        return []
    input_grids = [input_grid for input_grid, _ in training_pairs]
    output_grids = [output_grid for _, output_grid in training_pairs]
    all_colors = color_inventory([*input_grids, *output_grids])
    backgrounds = {background_color(grid) for grid in input_grids}
    seed_colors = tuple(color for color in all_colors if color not in backgrounds)
    candidates: list[Hypothesis] = []
    for seed_color in seed_colors:
        for fill_color in all_colors:
            for direction in ("up", "down", "left", "right"):
                candidates.append(
                    Hypothesis(
                        "line_extend",
                        _parameter_tuple(
                            direction=direction,
                            fill_color=fill_color,
                            seed_color=seed_color,
                        ),
                        description_length=4,
                    )
                )
            candidates.append(
                Hypothesis(
                    "row_span_fill",
                    _parameter_tuple(fill_color=fill_color, seed_color=seed_color),
                    description_length=4,
                )
            )
    return candidates
