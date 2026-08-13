"""Generic, inspectable hypothesis operators for the first ARC123 learner."""

from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
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
        if self.kind == "dihedral_transform":
            return self._dihedral_transform(input_grid)
        if self.kind == "translate":
            return self._translate(input_grid)
        if self.kind == "line_extend":
            return self._line_extend(input_grid)
        if self.kind == "row_span_fill":
            return self._row_span_fill(input_grid)
        if self.kind == "tile_repeat":
            return self._tile_repeat(input_grid)
        if self.kind == "dihedral_tile":
            return self._dihedral_tile(input_grid)
        if self.kind == "self_mask_macro_stamp":
            return self._self_mask_macro_stamp(input_grid)
        if self.kind == "axis_mode_denoise":
            return self._axis_mode_denoise(input_grid)
        if self.kind == "self_contained_subset_crop":
            return self._self_contained_subset_crop(input_grid)
        if self.kind == "frame_interior_crop":
            return self._frame_interior_crop(input_grid)
        if self.kind == "central_separator_cellwise_combine":
            return self._central_separator_cellwise_combine(input_grid)
        if self.kind == "adjacent_bilateral_cellwise_combine":
            return self._adjacent_bilateral_cellwise_combine(input_grid)
        if self.kind == "distinct_nonbackground_scale":
            return self._distinct_nonbackground_scale(input_grid)
        if self.kind == "separated_panel_cellwise_combine":
            return self._separated_panel_cellwise_combine(input_grid)
        if self.kind == "anti_diagonal_nonbackground_stream":
            return self._anti_diagonal_nonbackground_stream(input_grid)
        if self.kind == "symmetric_foreground_quadrant_crop":
            return self._symmetric_foreground_quadrant_crop(input_grid)
        if self.kind == "uniform_block_self_stamp_fractal":
            return self._uniform_block_self_stamp_fractal(input_grid)
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

    def _dihedral_transform(self, input_grid: Grid) -> PartialGrid:
        axis = str(self.parameter_map["axis"])
        height = len(input_grid)
        width = len(input_grid[0])
        if axis == "transpose":
            return tuple(
                tuple(input_grid[row][column] for row in range(height))
                for column in range(width)
            )
        if axis == "anti_transpose":
            return tuple(
                tuple(input_grid[height - 1 - row][width - 1 - column] for row in range(height))
                for column in range(width)
            )
        if axis == "rotate_90":
            return tuple(
                tuple(input_grid[height - 1 - row][column] for row in range(height))
                for column in range(width)
            )
        if axis == "rotate_270":
            return tuple(
                tuple(input_grid[row][width - 1 - column] for row in range(height))
                for column in range(width)
            )
        raise ValueError(f"unknown dihedral transform axis: {axis}")

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
        selection = str(parameters.get("selection", "all"))
        if selection not in {"all", "global_minimum"}:
            raise ValueError(f"unknown row-span selection: {selection}")
        background = background_color(input_grid)
        output = [list(row) for row in input_grid]
        spans: list[tuple[int, int, int]] = []
        for row_index, row in enumerate(input_grid):
            seed_columns = [
                column_index for column_index, color in enumerate(row) if color == seed_color
            ]
            if len(seed_columns) < 2:
                continue
            spans.append((row_index, min(seed_columns), max(seed_columns)))
        if selection == "global_minimum" and spans:
            minimum_span = min(right - left for _, left, right in spans)
            spans = [
                (row_index, left, right)
                for row_index, left, right in spans
                if right - left == minimum_span
            ]
        for row_index, left, right in spans:
            for column_index in range(left, right + 1):
                if output[row_index][column_index] == background:
                    output[row_index][column_index] = fill_color
        return tuple(tuple(row) for row in output)

    def _tile_repeat(self, input_grid: Grid) -> PartialGrid:
        parameters = self.parameter_map
        row_factor = int(parameters["row_factor"])
        column_factor = int(parameters["column_factor"])
        if row_factor < 1 or column_factor < 1:
            raise ValueError("tile factors must be positive")
        height = len(input_grid)
        width = len(input_grid[0])
        return tuple(
            tuple(
                input_grid[row_index % height][column_index % width]
                for column_index in range(width * column_factor)
            )
            for row_index in range(height * row_factor)
        )

    def _dihedral_tile(self, input_grid: Grid) -> PartialGrid:
        parameters = self.parameter_map
        row_factor = int(parameters["row_factor"])
        column_factor = int(parameters["column_factor"])
        template = str(parameters["template"]).split(";")
        if row_factor < 1 or column_factor < 1 or len(template) != row_factor * column_factor:
            raise ValueError("dihedral tile parameters are malformed")
        height = len(input_grid)
        width = len(input_grid[0])
        orientations: dict[str, Grid] = {
            "identity": input_grid,
            "flip_lr": tuple(tuple(reversed(row)) for row in input_grid),
            "flip_tb": tuple(reversed(input_grid)),
            "rotate_180": tuple(tuple(reversed(row)) for row in reversed(input_grid)),
        }
        if height == width:
            orientations.update(
                {
                    "rotate_90": tuple(
                        tuple(input_grid[height - 1 - column][row] for column in range(width))
                        for row in range(height)
                    ),
                    "rotate_270": tuple(
                        tuple(input_grid[column][width - 1 - row] for column in range(width))
                        for row in range(height)
                    ),
                    "transpose": tuple(
                        tuple(input_grid[column][row] for column in range(width))
                        for row in range(height)
                    ),
                    "anti_transpose": tuple(
                        tuple(
                            input_grid[height - 1 - column][width - 1 - row]
                            for column in range(width)
                        )
                        for row in range(height)
                    ),
                }
            )
        blank = tuple(tuple(background_color(input_grid) for _ in range(width)) for _ in range(height))
        blocks = [orientations[label] if label != "blank" else blank for label in template]
        return tuple(
            tuple(
                cell
                for column_block in range(column_factor)
                for cell in blocks[row_block * column_factor + column_block][row]
            )
            for row_block in range(row_factor)
            for row in range(height)
        )

    def _self_mask_macro_stamp(self, input_grid: Grid) -> Optional[PartialGrid]:
        """Stamp an input-derived template into a macro-grid selected by input cells.

        The selector is a relative color role rather than a task-specific color.  The
        output has one input-sized block for each input cell; selected cells receive
        the learned template and all other blocks receive the learned blank color.
        """

        parameters = self.parameter_map
        selector_name = str(parameters["selector"])
        template_name = str(parameters["template"])
        blank_color = int(parameters["blank_color"])
        selector = _self_macro_selector(input_grid, selector_name)
        if selector is None:
            return None

        height = len(input_grid)
        width = len(input_grid[0])
        if template_name == "input":
            template: Grid = input_grid
        elif template_name == "selected_mask_other_color":
            other_colors = {
                color
                for row_index, row in enumerate(input_grid)
                for column_index, color in enumerate(row)
                if not selector[row_index][column_index]
            }
            if len(other_colors) != 1:
                return None
            other_color = next(iter(other_colors))
            if other_color == blank_color:
                return None
            template = tuple(
                tuple(
                    other_color if selector[row_index][column_index] else blank_color
                    for column_index in range(width)
                )
                for row_index in range(height)
            )
        else:
            raise ValueError(f"unknown self-mask macro template: {template_name}")

        return tuple(
            tuple(
                template[row_index % height][column_index % width]
                if selector[row_index // height][column_index // width]
                else blank_color
                for column_index in range(width * width)
            )
            for row_index in range(height * height)
        )

    def _axis_mode_denoise(self, input_grid: Grid) -> Optional[PartialGrid]:
        """Fill each row or column with its input-derived unique modal color.

        The dominant axis is inferred independently for every input grid.  Its score
        is the total number of modal cells across its lines; row and column scores
        have the same ``height * width`` denominator.  Tied line modes or tied axis
        support leave the theory incomplete instead of silently choosing a color or
        orientation.
        """

        row_projection = _axis_mode_projection(input_grid, "row")
        column_projection = _axis_mode_projection(input_grid, "column")
        if row_projection is None or column_projection is None:
            return None
        row_grid, row_support = row_projection
        column_grid, column_support = column_projection
        if row_support == column_support:
            return None
        return row_grid if row_support > column_support else column_grid

    def _self_contained_subset_crop(self, input_grid: Grid) -> Optional[PartialGrid]:
        """Crop the unique smallest rectangle closed under an input color subset.

        A candidate subset contributes every row and column containing one of its
        colors.  Its induced rectangle is valid only when every cell inside it has a
        color from that same subset.  The operation uses no learned color identity:
        it returns a crop only when the smallest valid rectangle is unique.
        """

        height = len(input_grid)
        width = len(input_grid[0])
        colors = tuple(sorted({color for row in input_grid for color in row}))
        if len(colors) < 2 or len(colors) > 10:
            return None
        candidates: list[tuple[int, PartialGrid]] = []
        for mask in range(1, (1 << len(colors)) - 1):
            selected_colors = {
                color for index, color in enumerate(colors) if mask & (1 << index)
            }
            coordinates = [
                (row_index, column_index)
                for row_index, row in enumerate(input_grid)
                for column_index, color in enumerate(row)
                if color in selected_colors
            ]
            top = min(row_index for row_index, _ in coordinates)
            bottom = max(row_index for row_index, _ in coordinates)
            left = min(column_index for _, column_index in coordinates)
            right = max(column_index for _, column_index in coordinates)
            if top == 0 and bottom == height - 1 and left == 0 and right == width - 1:
                continue
            crop = tuple(
                tuple(input_grid[row_index][column_index] for column_index in range(left, right + 1))
                for row_index in range(top, bottom + 1)
            )
            if any(color not in selected_colors for row in crop for color in row):
                continue
            candidates.append(((bottom - top + 1) * (right - left + 1), crop))
        if not candidates:
            return None
        minimum_area = min(area for area, _ in candidates)
        minimum_crops = {
            crop for area, crop in candidates if area == minimum_area
        }
        if len(minimum_crops) != 1:
            return None
        return next(iter(minimum_crops))

    def _frame_interior_crop(self, input_grid: Grid) -> Optional[PartialGrid]:
        """Extract the interior of the unique largest uniform rectangular outline."""

        frame = _unique_largest_uniform_frame(input_grid)
        if frame is None:
            return None
        top, left, bottom, right = frame
        return tuple(
            tuple(input_grid[row_index][column_index] for column_index in range(left + 1, right))
            for row_index in range(top + 1, bottom)
        )

    def _central_separator_cellwise_combine(
        self, input_grid: Grid
    ) -> Optional[PartialGrid]:
        """Apply a learned pair-to-output table across a visible central separator."""

        parameters = self.parameter_map
        axis = str(parameters["axis"])
        table = _decode_cellwise_table(str(parameters["table"]))
        panels = _central_separator_panels(input_grid, axis)
        if panels is None:
            return None
        first_panel, second_panel = panels
        output: list[tuple[int, ...]] = []
        for first_row, second_row in zip(first_panel, second_panel):
            output_row: list[int] = []
            for first_color, second_color in zip(first_row, second_row):
                pair = (first_color, second_color)
                if pair not in table:
                    return None
                output_row.append(table[pair])
            output.append(tuple(output_row))
        return tuple(output)

    def _adjacent_bilateral_cellwise_combine(
        self, input_grid: Grid
    ) -> Optional[PartialGrid]:
        """Apply a learned pair table across two adjacent equal input panels."""

        parameters = self.parameter_map
        axis = str(parameters["axis"])
        table = _decode_cellwise_table(str(parameters["table"]))
        panels = _adjacent_bilateral_panels(input_grid, axis)
        if panels is None:
            return None
        first_panel, second_panel = panels
        output: list[tuple[int, ...]] = []
        for first_row, second_row in zip(first_panel, second_panel):
            output_row: list[int] = []
            for first_color, second_color in zip(first_row, second_row):
                pair = (first_color, second_color)
                if pair not in table:
                    return None
                output_row.append(table[pair])
            output.append(tuple(output_row))
        return tuple(output)

    def _distinct_nonbackground_scale(self, input_grid: Grid) -> Optional[PartialGrid]:
        """Scale each cell by the current grid's uniquely inferred non-background count."""

        background = _unique_background_color(input_grid)
        if background is None:
            return None
        factor = len(
            {color for row in input_grid for color in row if color != background}
        )
        if factor < 2:
            return None
        expanded_rows = [
            tuple(color for input_color in row for color in (input_color,) * factor)
            for row in input_grid
        ]
        return tuple(row for row in expanded_rows for _ in range(factor))

    def _separated_panel_cellwise_combine(
        self, input_grid: Grid
    ) -> Optional[PartialGrid]:
        """Apply a visible tuple table across three or more evenly separated panels."""

        parameters = self.parameter_map
        axis = str(parameters["axis"])
        panel_count = int(parameters["panel_count"])
        table = _decode_multi_panel_table(str(parameters["table"]))
        panels = _separated_equal_panels(input_grid, axis, panel_count)
        if panels is None:
            return None
        output: list[tuple[int, ...]] = []
        for panel_rows in zip(*panels):
            output_row: list[int] = []
            for panel_colors in zip(*panel_rows):
                output_color = table.get(tuple(panel_colors))
                if output_color is None:
                    return None
                output_row.append(output_color)
            output.append(tuple(output_row))
        return tuple(output)

    def _anti_diagonal_nonbackground_stream(
        self, input_grid: Grid
    ) -> Optional[PartialGrid]:
        """Expand a one-row signal into anti-diagonal streams of its visible values."""

        if len(input_grid) != 1:
            return None
        raw_background = self.parameter_map.get("background_color")
        background = (
            _unique_background_color(input_grid)
            if raw_background is None
            else int(raw_background)
        )
        if background is None:
            return None
        source_row = input_grid[0]
        if background not in source_row:
            return None
        nonbackground_count = sum(color != background for color in source_row)
        if not nonbackground_count:
            return None
        side_length = len(source_row) * nonbackground_count
        if side_length > 30:
            return None
        output = [[background for _ in range(side_length)] for _ in range(side_length)]
        for source_column, color in enumerate(source_row):
            if color == background:
                continue
            for row_index in range(side_length):
                column_index = side_length - 1 + source_column - row_index
                if 0 <= column_index < side_length:
                    output[row_index][column_index] = color
        return tuple(tuple(row) for row in output)

    def _symmetric_foreground_quadrant_crop(
        self, input_grid: Grid
    ) -> Optional[PartialGrid]:
        """Extract one learned quadrant from a doubly reflective foreground box."""

        parameters = self.parameter_map
        quadrant = str(parameters["quadrant"])
        foreground_bbox = _unique_foreground_bbox(input_grid)
        if foreground_bbox is None:
            return None
        _, top, left, bottom, right = foreground_bbox
        height = bottom - top + 1
        width = right - left + 1
        if height < 2 or width < 2 or height % 2 or width % 2:
            return None
        box = tuple(
            tuple(input_grid[row_index][column_index] for column_index in range(left, right + 1))
            for row_index in range(top, bottom + 1)
        )
        if box != tuple(tuple(reversed(row)) for row in box) or box != tuple(reversed(box)):
            return None
        half_height = height // 2
        half_width = width // 2
        offsets = {
            "top_left": (0, 0),
            "top_right": (0, half_width),
            "bottom_left": (half_height, 0),
            "bottom_right": (half_height, half_width),
        }
        if quadrant not in offsets:
            raise ValueError(f"unknown symmetric foreground quadrant: {quadrant}")
        top_offset, left_offset = offsets[quadrant]
        return tuple(
            tuple(
                box[row_index][column_index]
                for column_index in range(left_offset, left_offset + half_width)
            )
            for row_index in range(top_offset, top_offset + half_height)
        )

    def _uniform_block_self_stamp_fractal(
        self, input_grid: Grid
    ) -> Optional[PartialGrid]:
        """Read a uniform block mask and stamp it into every occupied block."""

        foreground_bbox = _unique_foreground_bbox(input_grid)
        if foreground_bbox is None:
            return None
        background, top, left, bottom, right = foreground_bbox
        crop_height = bottom - top + 1
        crop_width = right - left + 1
        if crop_height != crop_width:
            return None
        block_side = isqrt(crop_height)
        if block_side < 2 or block_side * block_side != crop_height:
            return None
        crop = tuple(
            tuple(input_grid[row_index][column_index] for column_index in range(left, right + 1))
            for row_index in range(top, bottom + 1)
        )
        foreground_colors = {
            color for row in crop for color in row if color != background
        }
        if len(foreground_colors) != 1:
            return None
        foreground = next(iter(foreground_colors))
        meta_pattern: list[tuple[bool, ...]] = []
        for block_row in range(block_side):
            meta_row: list[bool] = []
            for block_column in range(block_side):
                block_colors = {
                    crop[row_index][column_index]
                    for row_index in range(block_row * block_side, (block_row + 1) * block_side)
                    for column_index in range(
                        block_column * block_side, (block_column + 1) * block_side
                    )
                }
                if block_colors == {background}:
                    meta_row.append(False)
                elif block_colors == {foreground}:
                    meta_row.append(True)
                else:
                    return None
            meta_pattern.append(tuple(meta_row))
        return tuple(
            tuple(
                foreground
                if meta_pattern[row_index // block_side][column_index // block_side]
                and meta_pattern[row_index % block_side][column_index % block_side]
                else background
                for column_index in range(crop_width)
            )
            for row_index in range(crop_height)
        )


def _same_shape_training_pairs(training_pairs: Sequence[TrainingPair]) -> bool:
    return all(
        len(input_grid) == len(output_grid)
        and len(input_grid[0]) == len(output_grid[0])
        for input_grid, output_grid in training_pairs
    )


def _unique_mode(values: Sequence[int]) -> Optional[tuple[int, int]]:
    """Return a unique modal color and its support, or ``None`` for a tie."""

    if not values:
        return None
    counts: dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    support = max(counts.values())
    modal_colors = [color for color, count in counts.items() if count == support]
    if len(modal_colors) != 1:
        return None
    return modal_colors[0], support


def _axis_mode_projection(
    input_grid: Grid, axis: str
) -> Optional[tuple[PartialGrid, int]]:
    """Project a grid by per-line unique modes and return summed modal support."""

    height = len(input_grid)
    width = len(input_grid[0])
    if axis == "row":
        line_modes: list[tuple[int, int]] = []
        for row in input_grid:
            mode = _unique_mode(row)
            if mode is None:
                return None
            line_modes.append(mode)
        return (
            tuple(
                tuple(line_modes[row_index][0] for _ in range(width))
                for row_index in range(height)
            ),
            sum(support for _, support in line_modes),
        )
    if axis == "column":
        line_modes = []
        for column_index in range(width):
            mode = _unique_mode(
                tuple(input_grid[row_index][column_index] for row_index in range(height))
            )
            if mode is None:
                return None
            line_modes.append(mode)
        return (
            tuple(
                tuple(line_modes[column_index][0] for column_index in range(width))
                for _ in range(height)
            ),
            sum(support for _, support in line_modes),
        )
    raise ValueError(f"unknown mode-denoise axis: {axis}")


def _unique_largest_uniform_frame(
    input_grid: Grid,
) -> Optional[tuple[int, int, int, int]]:
    """Return the unique maximum-area non-solid uniform rectangular outline."""

    height = len(input_grid)
    width = len(input_grid[0])
    candidates: list[tuple[int, tuple[int, int, int, int]]] = []
    for top in range(height - 2):
        for bottom in range(top + 2, height):
            for left in range(width - 2):
                for right in range(left + 2, width):
                    frame_color = input_grid[top][left]
                    border_matches = (
                        all(input_grid[top][column] == frame_color for column in range(left, right + 1))
                        and all(
                            input_grid[bottom][column] == frame_color
                            for column in range(left, right + 1)
                        )
                        and all(
                            input_grid[row][left] == frame_color
                            for row in range(top + 1, bottom)
                        )
                        and all(
                            input_grid[row][right] == frame_color
                            for row in range(top + 1, bottom)
                        )
                    )
                    if not border_matches:
                        continue
                    if all(
                        input_grid[row][column] == frame_color
                        for row in range(top + 1, bottom)
                        for column in range(left + 1, right)
                    ):
                        continue
                    candidates.append(
                        (
                            (bottom - top - 1) * (right - left - 1),
                            (top, left, bottom, right),
                        )
                    )
    if not candidates:
        return None
    maximum_area = max(area for area, _ in candidates)
    maximum_frames = [frame for area, frame in candidates if area == maximum_area]
    return maximum_frames[0] if len(maximum_frames) == 1 else None


def _central_separator_panels(
    input_grid: Grid, axis: str
) -> Optional[tuple[Grid, Grid]]:
    """Split equal panels only at a uniform central divider line."""

    height = len(input_grid)
    width = len(input_grid[0])
    if axis == "vertical":
        if width < 3 or width % 2 != 1:
            return None
        divider_column = width // 2
        if len({input_grid[row][divider_column] for row in range(height)}) != 1:
            return None
        return (
            tuple(tuple(row[:divider_column]) for row in input_grid),
            tuple(tuple(row[divider_column + 1 :]) for row in input_grid),
        )
    if axis == "horizontal":
        if height < 3 or height % 2 != 1:
            return None
        divider_row = height // 2
        if len(set(input_grid[divider_row])) != 1:
            return None
        return input_grid[:divider_row], input_grid[divider_row + 1 :]
    raise ValueError(f"unknown central separator axis: {axis}")


def _adjacent_bilateral_panels(
    input_grid: Grid, axis: str
) -> Optional[tuple[Grid, Grid]]:
    """Split a grid into exactly two adjacent, equally shaped panels."""

    height = len(input_grid)
    width = len(input_grid[0])
    if axis == "vertical":
        if width < 2 or width % 2:
            return None
        split_column = width // 2
        return (
            tuple(tuple(row[:split_column]) for row in input_grid),
            tuple(tuple(row[split_column:]) for row in input_grid),
        )
    if axis == "horizontal":
        if height < 2 or height % 2:
            return None
        split_row = height // 2
        return input_grid[:split_row], input_grid[split_row:]
    raise ValueError(f"unknown adjacent bilateral axis: {axis}")


def _separated_equal_panels(
    input_grid: Grid, axis: str, panel_count: int
) -> Optional[tuple[Grid, ...]]:
    """Split three or more equal panels only at same-color uniform divider lines."""

    if panel_count < 3:
        return None
    background = _unique_background_color(input_grid)
    if background is None:
        return None
    height = len(input_grid)
    width = len(input_grid[0])
    length = width if axis == "vertical" else height
    remaining_length = length - (panel_count - 1)
    if remaining_length < panel_count or remaining_length % panel_count:
        return None
    panel_span = remaining_length // panel_count
    divider_indices = [
        panel_span + index * (panel_span + 1) for index in range(panel_count - 1)
    ]
    if axis == "vertical":
        divider_colors = [
            {input_grid[row_index][column_index] for row_index in range(height)}
            for column_index in divider_indices
        ]
        if any(len(colors) != 1 for colors in divider_colors):
            return None
        divider_color = next(iter(divider_colors[0]))
        if divider_color == background or any(colors != {divider_color} for colors in divider_colors):
            return None
        return tuple(
            tuple(
                tuple(row[start_column : start_column + panel_span])
                for row in input_grid
            )
            for start_column in range(0, width, panel_span + 1)
        )
    if axis == "horizontal":
        divider_colors = [set(input_grid[row_index]) for row_index in divider_indices]
        if any(len(colors) != 1 for colors in divider_colors):
            return None
        divider_color = next(iter(divider_colors[0]))
        if divider_color == background or any(colors != {divider_color} for colors in divider_colors):
            return None
        return tuple(
            tuple(input_grid[start_row : start_row + panel_span])
            for start_row in range(0, height, panel_span + 1)
        )
    raise ValueError(f"unknown separated panel axis: {axis}")


def _encode_cellwise_table(table: dict[tuple[int, int], int]) -> str:
    return ";".join(
        f"{first_color}:{second_color}:{output_color}"
        for (first_color, second_color), output_color in sorted(table.items())
    )


def _decode_cellwise_table(encoded: str) -> dict[tuple[int, int], int]:
    table: dict[tuple[int, int], int] = {}
    if not encoded:
        raise ValueError("cellwise table must not be empty")
    for entry in encoded.split(";"):
        fields = entry.split(":")
        if len(fields) != 3:
            raise ValueError("cellwise table entry is malformed")
        first_color, second_color, output_color = (int(field) for field in fields)
        pair = (first_color, second_color)
        if pair in table and table[pair] != output_color:
            raise ValueError("cellwise table assigns conflicting outputs")
        table[pair] = output_color
    return table


def _encode_multi_panel_table(table: dict[tuple[int, ...], int]) -> str:
    return ";".join(
        f"{','.join(str(color) for color in panel_colors)}:{output_color}"
        for panel_colors, output_color in sorted(table.items())
    )


def _decode_multi_panel_table(encoded: str) -> dict[tuple[int, ...], int]:
    table: dict[tuple[int, ...], int] = {}
    if not encoded:
        raise ValueError("multi-panel table must not be empty")
    for entry in encoded.split(";"):
        raw_inputs, separator, raw_output = entry.rpartition(":")
        if not separator or not raw_inputs or not raw_output:
            raise ValueError("multi-panel table entry is malformed")
        panel_colors = tuple(int(color) for color in raw_inputs.split(","))
        if not panel_colors:
            raise ValueError("multi-panel table entry has no panel values")
        output_color = int(raw_output)
        prior = table.get(panel_colors)
        if prior is not None and prior != output_color:
            raise ValueError("multi-panel table assigns conflicting outputs")
        table[panel_colors] = output_color
    return table


def _unique_background_color(input_grid: Grid) -> Optional[int]:
    """Return a unique modal color, retaining uncertainty when the mode ties."""

    counts: dict[int, int] = {}
    for row in input_grid:
        for color in row:
            counts[color] = counts.get(color, 0) + 1
    maximum_count = max(counts.values())
    candidates = [color for color, count in counts.items() if count == maximum_count]
    return candidates[0] if len(candidates) == 1 else None


def _unique_foreground_bbox(
    input_grid: Grid,
) -> Optional[tuple[int, int, int, int, int]]:
    """Return the modal background and foreground bounding box when both are defined."""

    background = _unique_background_color(input_grid)
    if background is None:
        return None
    cells = [
        (row_index, column_index)
        for row_index, row in enumerate(input_grid)
        for column_index, color in enumerate(row)
        if color != background
    ]
    if not cells:
        return None
    return (
        background,
        min(row_index for row_index, _ in cells),
        min(column_index for _, column_index in cells),
        max(row_index for row_index, _ in cells),
        max(column_index for _, column_index in cells),
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


def _dihedral_transform_candidates(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    """Infer shape-aware coordinate transforms directly from visible examples."""

    axes = ("transpose", "anti_transpose", "rotate_90", "rotate_270")
    candidates: list[Hypothesis] = []
    for axis in axes:
        hypothesis = Hypothesis(
            "dihedral_transform",
            _parameter_tuple(axis=axis),
            description_length=2,
        )
        if all(hypothesis.predict(input_grid) == _full(output_grid) for input_grid, output_grid in training_pairs):
            candidates.append(hypothesis)
    return candidates


def _tile_repeat_candidates(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    factors: set[tuple[int, int]] = set()
    for input_grid, output_grid in training_pairs:
        input_height, input_width = len(input_grid), len(input_grid[0])
        output_height, output_width = len(output_grid), len(output_grid[0])
        if output_height % input_height or output_width % input_width:
            return []
        factors.add((output_height // input_height, output_width // input_width))
    if len(factors) != 1:
        return []
    row_factor, column_factor = factors.pop()
    if row_factor == 1 and column_factor == 1:
        return []
    return [
        Hypothesis(
            "tile_repeat",
            _parameter_tuple(row_factor=row_factor, column_factor=column_factor),
            description_length=3,
        )
    ]


def _dihedral_orientations(input_grid: Grid) -> dict[str, Grid]:
    height = len(input_grid)
    width = len(input_grid[0])
    orientations: dict[str, Grid] = {
        "identity": input_grid,
        "flip_lr": tuple(tuple(reversed(row)) for row in input_grid),
        "flip_tb": tuple(reversed(input_grid)),
        "rotate_180": tuple(tuple(reversed(row)) for row in reversed(input_grid)),
    }
    if height == width:
        orientations.update(
            {
                "rotate_90": tuple(
                    tuple(input_grid[height - 1 - column][row] for column in range(width))
                    for row in range(height)
                ),
                "rotate_270": tuple(
                    tuple(input_grid[column][width - 1 - row] for column in range(width))
                    for row in range(height)
                ),
                "transpose": tuple(
                    tuple(input_grid[column][row] for column in range(width))
                    for row in range(height)
                ),
                "anti_transpose": tuple(
                    tuple(
                        input_grid[height - 1 - column][width - 1 - row]
                        for column in range(width)
                    )
                    for row in range(height)
                ),
            }
        )
    return orientations


def _self_macro_selector(
    input_grid: Grid, selector_name: str
) -> Optional[tuple[tuple[bool, ...], ...]]:
    """Return a role-based mask without carrying an input color across examples."""

    counts: dict[int, int] = {}
    for row in input_grid:
        for color in row:
            counts[color] = counts.get(color, 0) + 1
    if selector_name == "most_frequent":
        selected_color = min(counts, key=lambda color: (-counts[color], color))
        return tuple(tuple(color == selected_color for color in row) for row in input_grid)
    if selector_name == "least_frequent":
        selected_color = min(counts, key=lambda color: (counts[color], color))
        return tuple(tuple(color == selected_color for color in row) for row in input_grid)
    if selector_name == "zero":
        if 0 not in counts:
            return None
        return tuple(tuple(color == 0 for color in row) for row in input_grid)
    if selector_name == "nonzero":
        if set(counts) == {0}:
            return None
        return tuple(tuple(color != 0 for color in row) for row in input_grid)
    raise ValueError(f"unknown self-mask macro selector: {selector_name}")


def _self_mask_macro_stamp_candidates(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    """Infer a visible-example-only macro stamping relation.

    This family deliberately requires output dimensions of ``H² × W²``: the input
    acts both as a source of a role-based selector and as the dimensions of the
    macro-grid.  Candidates are retained only when one relative selector and one
    template relation explain every demonstrated output exactly.
    """

    if not training_pairs:
        return []
    for input_grid, output_grid in training_pairs:
        height = len(input_grid)
        width = len(input_grid[0])
        if len(output_grid) != height * height or len(output_grid[0]) != width * width:
            return []
    output_color_sets = [
        {color for row in output_grid for color in row}
        for _, output_grid in training_pairs
    ]
    blank_candidates = set(output_color_sets[0])
    for output_colors in output_color_sets[1:]:
        blank_candidates.intersection_update(output_colors)
    candidates: list[Hypothesis] = []
    for blank_color in sorted(blank_candidates):
        for selector_name in ("most_frequent", "least_frequent", "zero", "nonzero"):
            for template_name in ("input", "selected_mask_other_color"):
                hypothesis = Hypothesis(
                    "self_mask_macro_stamp",
                    _parameter_tuple(
                        blank_color=blank_color,
                        selector=selector_name,
                        template=template_name,
                    ),
                    description_length=(
                        5 if template_name == "input" else 6
                    ),
                )
                if all(
                    hypothesis.predict(input_grid) == _full(output_grid)
                    for input_grid, output_grid in training_pairs
                ):
                    candidates.append(hypothesis)
    return candidates


def _axis_mode_denoise_candidates(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    """Retain the dynamic line-mode projection only when all demonstrations fit."""

    if not training_pairs or not _same_shape_training_pairs(training_pairs):
        return []
    hypothesis = Hypothesis("axis_mode_denoise", description_length=4)
    if all(
        hypothesis.predict(input_grid) == _full(output_grid)
        for input_grid, output_grid in training_pairs
    ):
        return [hypothesis]
    return []


def _self_contained_subset_crop_candidates(
    training_pairs: Sequence[TrainingPair],
) -> list[Hypothesis]:
    """Keep a dynamic input-color crop only when every visible output agrees."""

    if not training_pairs:
        return []
    hypothesis = Hypothesis("self_contained_subset_crop", description_length=8)
    if all(
        hypothesis.predict(input_grid) == _full(output_grid)
        for input_grid, output_grid in training_pairs
    ):
        return [hypothesis]
    return []


def _frame_interior_crop_candidates(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    """Keep frame extraction only when every visible output agrees."""

    if not training_pairs:
        return []
    hypothesis = Hypothesis("frame_interior_crop", description_length=5)
    if all(
        hypothesis.predict(input_grid) == _full(output_grid)
        for input_grid, output_grid in training_pairs
    ):
        return [hypothesis]
    return []


def _central_separator_cellwise_combine_candidates(
    training_pairs: Sequence[TrainingPair],
) -> list[Hypothesis]:
    """Infer a visible-panel lookup table and retain only exact demonstrations."""

    candidates: list[Hypothesis] = []
    for axis in ("vertical", "horizontal"):
        table: dict[tuple[int, int], int] = {}
        valid = bool(training_pairs)
        for input_grid, output_grid in training_pairs:
            panels = _central_separator_panels(input_grid, axis)
            if panels is None:
                valid = False
                break
            first_panel, second_panel = panels
            if (
                len(output_grid) != len(first_panel)
                or len(output_grid[0]) != len(first_panel[0])
            ):
                valid = False
                break
            for first_row, second_row, output_row in zip(
                first_panel, second_panel, output_grid
            ):
                for first_color, second_color, output_color in zip(
                    first_row, second_row, output_row
                ):
                    pair = (first_color, second_color)
                    prior = table.get(pair)
                    if prior is not None and prior != output_color:
                        valid = False
                        break
                    table[pair] = output_color
                if not valid:
                    break
            if not valid:
                break
        if not valid or not table:
            continue
        hypothesis = Hypothesis(
            "central_separator_cellwise_combine",
            _parameter_tuple(axis=axis, table=_encode_cellwise_table(table)),
            description_length=4 + len(table),
        )
        if all(
            hypothesis.predict(input_grid) == _full(output_grid)
            for input_grid, output_grid in training_pairs
        ):
            candidates.append(hypothesis)
    return candidates


def _adjacent_bilateral_cellwise_combine_candidates(
    training_pairs: Sequence[TrainingPair],
) -> list[Hypothesis]:
    """Infer one unambiguous adjacent-panel table from visible demonstrations."""

    candidates: list[Hypothesis] = []
    for axis in ("vertical", "horizontal"):
        table: dict[tuple[int, int], int] = {}
        valid = bool(training_pairs)
        for input_grid, output_grid in training_pairs:
            panels = _adjacent_bilateral_panels(input_grid, axis)
            if panels is None:
                valid = False
                break
            first_panel, second_panel = panels
            if (
                len(output_grid) != len(first_panel)
                or len(output_grid[0]) != len(first_panel[0])
            ):
                valid = False
                break
            for first_row, second_row, output_row in zip(
                first_panel, second_panel, output_grid
            ):
                for first_color, second_color, output_color in zip(
                    first_row, second_row, output_row
                ):
                    pair = (first_color, second_color)
                    prior = table.get(pair)
                    if prior is not None and prior != output_color:
                        valid = False
                        break
                    table[pair] = output_color
                if not valid:
                    break
            if not valid:
                break
        if not valid or not table:
            continue
        hypothesis = Hypothesis(
            "adjacent_bilateral_cellwise_combine",
            _parameter_tuple(axis=axis, table=_encode_cellwise_table(table)),
            description_length=4 + len(table),
        )
        if all(
            hypothesis.predict(input_grid) == _full(output_grid)
            for input_grid, output_grid in training_pairs
        ):
            candidates.append(hypothesis)
    return candidates if len(candidates) == 1 else []


def _distinct_nonbackground_scale_candidates(
    training_pairs: Sequence[TrainingPair],
) -> list[Hypothesis]:
    """Keep dynamic pixel scaling only when every demonstration agrees."""

    if not training_pairs:
        return []
    hypothesis = Hypothesis("distinct_nonbackground_scale", description_length=4)
    if all(
        hypothesis.predict(input_grid) == _full(output_grid)
        for input_grid, output_grid in training_pairs
    ):
        return [hypothesis]
    return []


def _separated_panel_cellwise_combine_candidates(
    training_pairs: Sequence[TrainingPair],
) -> list[Hypothesis]:
    """Infer one unambiguous visible tuple table over regularly separated panels."""

    if not training_pairs:
        return []
    candidates: list[Hypothesis] = []
    for axis in ("vertical", "horizontal"):
        minimum_length = min(
            (len(input_grid[0]) if axis == "vertical" else len(input_grid))
            for input_grid, _ in training_pairs
        )
        maximum_panel_count = (minimum_length + 1) // 2
        for panel_count in range(3, maximum_panel_count + 1):
            table: dict[tuple[int, ...], int] = {}
            valid = bool(training_pairs)
            for input_grid, output_grid in training_pairs:
                panels = _separated_equal_panels(input_grid, axis, panel_count)
                if panels is None:
                    valid = False
                    break
                if (
                    len(output_grid) != len(panels[0])
                    or len(output_grid[0]) != len(panels[0][0])
                ):
                    valid = False
                    break
                for panel_rows, output_row in zip(zip(*panels), output_grid):
                    for panel_colors, output_color in zip(zip(*panel_rows), output_row):
                        key = tuple(panel_colors)
                        prior = table.get(key)
                        if prior is not None and prior != output_color:
                            valid = False
                            break
                        table[key] = output_color
                    if not valid:
                        break
                if not valid:
                    break
            if not valid or not table:
                continue
            hypothesis = Hypothesis(
                "separated_panel_cellwise_combine",
                _parameter_tuple(
                    axis=axis,
                    panel_count=panel_count,
                    table=_encode_multi_panel_table(table),
                ),
                description_length=4 + panel_count + len(table),
            )
            if all(
                hypothesis.predict(input_grid) == _full(output_grid)
                for input_grid, output_grid in training_pairs
            ):
                candidates.append(hypothesis)
    return candidates if len(candidates) == 1 else []


def _anti_diagonal_nonbackground_stream_candidates(
    training_pairs: Sequence[TrainingPair],
) -> list[Hypothesis]:
    """Infer a shared visible output background for dynamic anti-diagonal streams."""

    if not training_pairs:
        return []
    shared_backgrounds: set[int] | None = None
    for input_grid, output_grid in training_pairs:
        background = _unique_background_color(output_grid)
        if background is None or all(background != color for row in input_grid for color in row):
            return []
        current_backgrounds = {background}
        shared_backgrounds = (
            current_backgrounds
            if shared_backgrounds is None
            else shared_backgrounds & current_backgrounds
        )
    if shared_backgrounds is None or len(shared_backgrounds) != 1:
        return []
    background = next(iter(shared_backgrounds))
    hypothesis = Hypothesis(
        "anti_diagonal_nonbackground_stream",
        _parameter_tuple(background_color=background),
        description_length=7,
    )
    if all(
        hypothesis.predict(input_grid) == _full(output_grid)
        for input_grid, output_grid in training_pairs
    ):
        return [hypothesis]
    return []


def _symmetric_foreground_quadrant_crop_candidates(
    training_pairs: Sequence[TrainingPair],
) -> list[Hypothesis]:
    """Infer one quadrant only when a reflective foreground box fixes it uniquely."""

    candidates = [
        Hypothesis(
            "symmetric_foreground_quadrant_crop",
            _parameter_tuple(quadrant=quadrant),
            description_length=6,
        )
        for quadrant in ("top_left", "top_right", "bottom_left", "bottom_right")
    ]
    exact_candidates = [
        hypothesis
        for hypothesis in candidates
        if training_pairs
        and all(
            hypothesis.predict(input_grid) == _full(output_grid)
            for input_grid, output_grid in training_pairs
        )
    ]
    if not exact_candidates:
        return []
    canonical = next(
        hypothesis
        for hypothesis in exact_candidates
        if hypothesis.parameter_map["quadrant"] == "top_left"
    )
    if all(
        hypothesis.predict(input_grid) == canonical.predict(input_grid)
        for hypothesis in exact_candidates
        for input_grid, _ in training_pairs
    ):
        return [canonical]
    return exact_candidates if len(exact_candidates) == 1 else []


def _uniform_block_self_stamp_fractal_candidates(
    training_pairs: Sequence[TrainingPair],
) -> list[Hypothesis]:
    """Keep the input-derived block fractal only when every demonstration agrees."""

    if not training_pairs:
        return []
    hypothesis = Hypothesis("uniform_block_self_stamp_fractal", description_length=7)
    if all(
        hypothesis.predict(input_grid) == _full(output_grid)
        for input_grid, output_grid in training_pairs
    ):
        return [hypothesis]
    return []


def _dihedral_tile_candidates(training_pairs: Sequence[TrainingPair]) -> list[Hypothesis]:
    factors: set[tuple[int, int]] = set()
    possible_labels: list[set[str]] | None = None
    label_order = (
        "identity",
        "flip_lr",
        "flip_tb",
        "rotate_180",
        "rotate_90",
        "rotate_270",
        "transpose",
        "anti_transpose",
        "blank",
    )
    for input_grid, output_grid in training_pairs:
        height, width = len(input_grid), len(input_grid[0])
        output_height, output_width = len(output_grid), len(output_grid[0])
        if output_height % height or output_width % width:
            return []
        row_factor, column_factor = output_height // height, output_width // width
        if row_factor == 1 and column_factor == 1:
            return []
        factors.add((row_factor, column_factor))
        orientations = _dihedral_orientations(input_grid)
        background = background_color(input_grid)
        example_labels: list[set[str]] = []
        for row_block in range(row_factor):
            for column_block in range(column_factor):
                block = tuple(
                    tuple(
                        output_grid[row_block * height + row][column_block * width + column]
                        for column in range(width)
                    )
                    for row in range(height)
                )
                labels = {name for name, transformed in orientations.items() if transformed == block}
                if all(cell == background for row in block for cell in row):
                    labels.add("blank")
                if not labels:
                    return []
                example_labels.append(labels)
        if possible_labels is None:
            possible_labels = example_labels
        else:
            if len(possible_labels) != len(example_labels):
                return []
            possible_labels = [
                previous & current
                for previous, current in zip(possible_labels, example_labels)
            ]
            if any(not labels for labels in possible_labels):
                return []
    if len(factors) != 1 or possible_labels is None:
        return []
    row_factor, column_factor = factors.pop()
    template = tuple(
        next(label for label in label_order if label in labels) for labels in possible_labels
    )
    if all(label == "identity" for label in template):
        return []
    return [
        Hypothesis(
            "dihedral_tile",
            _parameter_tuple(
                column_factor=column_factor,
                row_factor=row_factor,
                template=";".join(template),
            ),
            description_length=5 + sum(label != "identity" for label in template),
        )
    ]


def propose_base_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[Hypothesis]:
    """Propose generic global relations before inspecting structured residuals."""

    if enabled_operator_families is None:
        enabled = frozenset(
            {
                "identity",
                "recolor",
                "mirror",
                "dihedral_transform",
                "translate",
                "self_mask_macro_stamp",
                "axis_mode_denoise",
                "self_contained_subset_crop",
                "frame_interior_crop",
                "central_separator_cellwise_combine",
                "adjacent_bilateral_cellwise_combine",
                "distinct_nonbackground_scale",
                "separated_panel_cellwise_combine",
                "anti_diagonal_nonbackground_stream",
                "symmetric_foreground_quadrant_crop",
                "uniform_block_self_stamp_fractal",
            }
        )
    else:
        enabled = frozenset(enabled_operator_families)
    candidates = [Hypothesis("identity", description_length=1)] if "identity" in enabled else []
    recolor_mapping = _infer_recolor_mapping(training_pairs)
    if recolor_mapping is not None and "recolor" in enabled:
        candidates.append(Hypothesis("recolor", recolor_mapping, description_length=2))
    if _same_shape_training_pairs(training_pairs):
        if "mirror" in enabled:
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
        if "translate" in enabled:
            candidates.extend(_translation_candidates(training_pairs))
    if "dihedral_transform" in enabled:
        candidates.extend(_dihedral_transform_candidates(training_pairs))
    if "repeat_tile" in enabled:
        candidates.extend(_tile_repeat_candidates(training_pairs))
    if "dihedral_tile" in enabled:
        candidates.extend(_dihedral_tile_candidates(training_pairs))
    if "self_mask_macro_stamp" in enabled:
        candidates.extend(_self_mask_macro_stamp_candidates(training_pairs))
    if "axis_mode_denoise" in enabled:
        candidates.extend(_axis_mode_denoise_candidates(training_pairs))
    if "self_contained_subset_crop" in enabled:
        candidates.extend(_self_contained_subset_crop_candidates(training_pairs))
    if "frame_interior_crop" in enabled:
        candidates.extend(_frame_interior_crop_candidates(training_pairs))
    if "central_separator_cellwise_combine" in enabled:
        candidates.extend(_central_separator_cellwise_combine_candidates(training_pairs))
    if "adjacent_bilateral_cellwise_combine" in enabled:
        candidates.extend(_adjacent_bilateral_cellwise_combine_candidates(training_pairs))
    if "distinct_nonbackground_scale" in enabled:
        candidates.extend(_distinct_nonbackground_scale_candidates(training_pairs))
    if "separated_panel_cellwise_combine" in enabled:
        candidates.extend(_separated_panel_cellwise_combine_candidates(training_pairs))
    if "anti_diagonal_nonbackground_stream" in enabled:
        candidates.extend(_anti_diagonal_nonbackground_stream_candidates(training_pairs))
    if "symmetric_foreground_quadrant_crop" in enabled:
        candidates.extend(_symmetric_foreground_quadrant_crop_candidates(training_pairs))
    if "uniform_block_self_stamp_fractal" in enabled:
        candidates.extend(_uniform_block_self_stamp_fractal_candidates(training_pairs))
    return candidates


def propose_structural_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[Hypothesis]:
    """Propose generic fill/extension relations only after residual-directed revision."""

    if enabled_operator_families is None:
        enabled = frozenset({"line_extend", "row_span_fill", "dihedral_tile"})
    else:
        enabled = frozenset(enabled_operator_families)
    candidates: list[Hypothesis] = []
    if _same_shape_training_pairs(training_pairs):
        input_grids = [input_grid for input_grid, _ in training_pairs]
        output_grids = [output_grid for _, output_grid in training_pairs]
        all_colors = color_inventory([*input_grids, *output_grids])
        backgrounds = {background_color(grid) for grid in input_grids}
        seed_colors = tuple(color for color in all_colors if color not in backgrounds)
        fill_colors = tuple(color for color in all_colors if color not in backgrounds)
        for seed_color in seed_colors:
            for fill_color in fill_colors:
                if "line_extend" in enabled:
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
                if "row_span_fill" in enabled:
                    candidates.append(
                        Hypothesis(
                            "row_span_fill",
                            _parameter_tuple(fill_color=fill_color, seed_color=seed_color),
                            description_length=4,
                        )
                    )
    if "dihedral_tile" in enabled:
        candidates.extend(_dihedral_tile_candidates(training_pairs))
    return candidates
