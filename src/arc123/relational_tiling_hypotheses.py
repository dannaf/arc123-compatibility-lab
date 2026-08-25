"""Generic relational tiling hypotheses using compact procedural state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .model import Grid, PartialGrid, TrainingPair


@dataclass(frozen=True)
class AlternatingHorizontalMirrorTile:
    """Tile an input; odd macro rows use a left-right reflected micro tile."""

    row_factor: int
    column_factor: int
    name: str = "alternating_horizontal_mirror_tile"
    description_length: int = 4

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "macro_row_parity -> micro_tile_orientation",
            "procedural_state_bits": 1,
            "even": "identity",
            "odd": "left_right_mirror",
            "forward_deterministic": True,
            "backward_semantics": "observed tile orientation identifies parity class",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        height = len(input_grid)
        width = len(input_grid[0])
        output: list[list[int]] = []
        for row in range(height * self.row_factor):
            macro_row = row // height
            micro_row = row % height
            out_row: list[int] = []
            for column in range(width * self.column_factor):
                micro_column = column % width
                source_column = width - 1 - micro_column if macro_row % 2 else micro_column
                out_row.append(input_grid[micro_row][source_column])
            output.append(out_row)
        return tuple(tuple(row) for row in output)


def propose_relational_tiling_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[AlternatingHorizontalMirrorTile]:
    if enabled_operator_families is not None and "alternating_mirror_tile" not in enabled_operator_families:
        return []
    factors: set[tuple[int, int]] = set()
    for input_grid, output_grid in training_pairs:
        input_height, input_width = len(input_grid), len(input_grid[0])
        output_height, output_width = len(output_grid), len(output_grid[0])
        if output_height % input_height or output_width % input_width:
            return []
        factors.add((output_height // input_height, output_width // input_width))
    if len(factors) != 1:
        return []
    row_factor, column_factor = next(iter(factors))
    if row_factor < 2 or column_factor < 1:
        return []
    candidate = AlternatingHorizontalMirrorTile(row_factor, column_factor)
    if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
        return [candidate]
    return []
