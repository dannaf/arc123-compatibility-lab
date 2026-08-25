"""Relational closure followed by symbolic macro rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color


@dataclass(frozen=True)
class DiagonalClosureMacroRender:
    """Seed NW-SE diagonals at logical resolution, then render 2x2 macrocells."""

    line_color: int
    name: str = "diagonal_closure_macro_render"
    description_length: int = 7

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "foreground_seed -> logical_NW_SE_diagonal_closure -> 2x2_macro_symbol",
            "seed_symbol": "solid_2x2_original_color",
            "closure_symbol": "2x2_main_diagonal_glyph",
            "scale": 2,
            "learned_line_color": self.line_color,
            "forward_deterministic": True,
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        if not input_grid or not input_grid[0]:
            return None
        background = background_color(input_grid)
        height, width = len(input_grid), len(input_grid[0])
        seeds = {
            (r, c): input_grid[r][c]
            for r in range(height)
            for c in range(width)
            if input_grid[r][c] != background
        }
        if not seeds:
            return None
        if self.line_color == background:
            return None
        diagonal_classes = {r - c for r, c in seeds}
        output = [[background for _ in range(2 * width)] for _ in range(2 * height)]
        for r in range(height):
            for c in range(width):
                top, left = 2 * r, 2 * c
                seed_color = seeds.get((r, c))
                if seed_color is not None:
                    for dr in (0, 1):
                        for dc in (0, 1):
                            output[top + dr][left + dc] = seed_color
                elif r - c in diagonal_classes:
                    output[top][left] = self.line_color
                    output[top + 1][left + 1] = self.line_color
        return tuple(tuple(row) for row in output)


def _infer_line_colors(training_pairs: Sequence[TrainingPair]) -> tuple[int, ...]:
    candidate_sets: list[set[int]] = []
    for input_grid, output_grid in training_pairs:
        input_colors = {value for row in input_grid for value in row}
        output_colors = {value for row in output_grid for value in row}
        introduced = output_colors - input_colors
        if not introduced:
            return ()
        candidate_sets.append(introduced)
    common = set.intersection(*candidate_sets)
    return tuple(sorted(common))


def propose_relational_macro_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[DiagonalClosureMacroRender]:
    if enabled_operator_families is not None and (
        "diagonal_closure_macro_render" not in enabled_operator_families
    ):
        return []
    if not training_pairs:
        return []
    if any(
        len(output_grid) != 2 * len(input_grid)
        or len(output_grid[0]) != 2 * len(input_grid[0])
        for input_grid, output_grid in training_pairs
    ):
        return []
    candidates: list[DiagonalClosureMacroRender] = []
    for line_color in _infer_line_colors(training_pairs):
        candidate = DiagonalClosureMacroRender(line_color)
        if all(
            candidate.predict(input_grid) == output_grid
            for input_grid, output_grid in training_pairs
        ):
            candidates.append(candidate)
    return candidates
