"""Generic geometric relations discovered from opened development counterexamples."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color


@dataclass(frozen=True)
class BottomAnchoredLeftShear:
    """Shift each foreground row left by its distance above the bottom row.

    The bottommost foreground row is the zero-displacement anchor.  A cell at
    row r moves by ``-(bottom-r)`` columns.  Cells translated outside the grid
    are clipped.  Color is carried by the translated cell; no task-specific
    palette value is learned.
    """

    name: str = "bottom_anchored_left_shear"
    description_length: int = 5

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "vertical_distance_from_bottom_anchor -> horizontal_displacement",
            "displacement": "delta_column = -(bottom_foreground_row - row)",
            "boundary_semantics": "clip translated cells outside grid",
            "forward_deterministic": True,
            "inverse_on_unclipped_support": "row-preserving right shear",
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        background = background_color(input_grid)
        foreground = [
            (row, column, color)
            for row, values in enumerate(input_grid)
            for column, color in enumerate(values)
            if color != background
        ]
        if not foreground:
            return None
        # Keep this production semantically narrow: one foreground material is
        # sheared as one geometric object.  Multi-color scenes remain UNKNOWN.
        if len({color for _, _, color in foreground}) != 1:
            return None
        bottom = max(row for row, _, _ in foreground)
        height = len(input_grid)
        width = len(input_grid[0])
        output = [[background for _ in range(width)] for _ in range(height)]
        for row, column, color in foreground:
            new_column = column - (bottom - row)
            if 0 <= new_column < width:
                output[row][new_column] = color
        return tuple(tuple(row) for row in output)


def propose_geometric_relation_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[BottomAnchoredLeftShear]:
    if enabled_operator_families is not None and (
        "bottom_anchored_left_shear" not in enabled_operator_families
    ):
        return []
    if not training_pairs:
        return []
    if any(
        len(input_grid) != len(output_grid)
        or len(input_grid[0]) != len(output_grid[0])
        for input_grid, output_grid in training_pairs
    ):
        return []
    candidate = BottomAnchoredLeftShear()
    return [
        candidate
    ] if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs) else []
