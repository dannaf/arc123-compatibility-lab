"""Frequency-extremum macro stamping as a reusable semantic callosal family."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .model import Grid, PartialGrid, TrainingPair


def _macro_shape(training_pairs: Sequence[TrainingPair]) -> bool:
    return bool(training_pairs) and all(
        len(output_grid) == len(input_grid) * len(input_grid)
        and len(output_grid[0]) == len(input_grid[0]) * len(input_grid[0])
        for input_grid, output_grid in training_pairs
    )


def _unique_frequency_extreme(grid: Grid, mode: str) -> int | None:
    counts = Counter(color for row in grid for color in row)
    if not counts:
        return None
    target_count = (max if mode == "most_frequent" else min)(counts.values())
    winners = [color for color, count in counts.items() if count == target_count]
    return winners[0] if len(winners) == 1 else None


@dataclass(frozen=True)
class FrequencyExtremumMacroStamp:
    """Stamp the whole input at macro positions selected by a frequency extreme."""

    mode: str
    blank_color: int
    name: str = "frequency_extremum_macro_stamp"
    description_length: int = 4

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "macro_cell_matches_frequency_extreme -> stamped_micro_grid",
            "frequency_predicate": self.mode,
            "blank_color": self.blank_color,
            "forward_deterministic": True,
            "backward_semantics": "nonblank output block certifies frequency-extremum macro source",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        trigger = _unique_frequency_extreme(input_grid, self.mode)
        height = len(input_grid)
        width = len(input_grid[0])
        if trigger is None:
            return tuple(
                tuple(None for _ in range(width * width))
                for _ in range(height * height)
            )
        output = [
            [self.blank_color for _ in range(width * width)]
            for _ in range(height * height)
        ]
        for macro_row in range(height):
            for macro_column in range(width):
                if input_grid[macro_row][macro_column] != trigger:
                    continue
                for micro_row in range(height):
                    for micro_column in range(width):
                        output[macro_row * height + micro_row][macro_column * width + micro_column] = input_grid[micro_row][micro_column]
        return tuple(tuple(row) for row in output)


def propose_frequency_macro_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[FrequencyExtremumMacroStamp]:
    if not _macro_shape(training_pairs):
        return []
    if enabled_operator_families is not None and "macro_micro_gate" not in enabled_operator_families:
        return []

    candidates: list[FrequencyExtremumMacroStamp] = []
    for mode in ("most_frequent", "least_frequent"):
        learned_blank: int | None = None
        valid = True
        for input_grid, output_grid in training_pairs:
            trigger = _unique_frequency_extreme(input_grid, mode)
            if trigger is None:
                valid = False
                break
            height = len(input_grid)
            width = len(input_grid[0])
            for macro_row in range(height):
                for macro_column in range(width):
                    block = tuple(
                        tuple(
                            output_grid[macro_row * height + row][macro_column * width + column]
                            for column in range(width)
                        )
                        for row in range(height)
                    )
                    if input_grid[macro_row][macro_column] == trigger:
                        if block != input_grid:
                            valid = False
                            break
                    else:
                        colors = {color for row in block for color in row}
                        if len(colors) != 1:
                            valid = False
                            break
                        blank = next(iter(colors))
                        if learned_blank is None:
                            learned_blank = blank
                        elif learned_blank != blank:
                            valid = False
                            break
                if not valid:
                    break
            if not valid:
                break
        if valid and learned_blank is not None:
            candidate = FrequencyExtremumMacroStamp(mode, learned_blank)
            if all(candidate.predict(x) == y for x, y in training_pairs):
                candidates.append(candidate)
    return candidates
