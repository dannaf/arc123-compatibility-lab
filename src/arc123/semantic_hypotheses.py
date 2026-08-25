"""Generic semantic-interface hypotheses for ARC123.

These operators are deliberately task-ID agnostic. They are proposed only from
visible training input/output structure and preserve UNKNOWN on unsupported
semantic keys. They implement issue #10's semantic callosal refinement ladder:
coordinate summaries, procedural runs, topology, and overlapping constraint
interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color


def _same_shape(training_pairs: Sequence[TrainingPair]) -> bool:
    return all(
        len(input_grid) == len(output_grid)
        and len(input_grid[0]) == len(output_grid[0])
        for input_grid, output_grid in training_pairs
    )


@dataclass(frozen=True)
class RowMarkerColumnMap:
    """Map a row's unique non-background marker column to a constant output row."""

    mapping: tuple[tuple[int, int], ...]
    name: str = "row_marker_column_to_constant_row"
    description_length: int = 4

    @property
    def callosal_summary(self) -> dict[str, object]:
        reverse: dict[int, list[int]] = {}
        for column, color in self.mapping:
            reverse.setdefault(color, []).append(column)
        return {
            "interface": "marker_column<->constant_row_color",
            "forward_rows": len(self.mapping),
            "forward_deterministic": True,
            "backward_deterministic": all(len(columns) == 1 for columns in reverse.values()),
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        background = background_color(input_grid)
        learned = dict(self.mapping)
        width = len(input_grid[0])
        rows: list[tuple[Optional[int], ...]] = []
        for row in input_grid:
            markers = [index for index, color in enumerate(row) if color != background]
            if len(markers) != 1 or markers[0] not in learned:
                rows.append(tuple(None for _ in range(width)))
                continue
            output_color = learned[markers[0]]
            rows.append(tuple(output_color for _ in range(width)))
        return tuple(rows)


@dataclass(frozen=True)
class ColumnDownwardPropagation:
    """Propagate the most recent non-background marker down each column."""

    name: str = "column_downward_propagation"
    description_length: int = 3

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "column_active_state->cell_effect",
            "forward_deterministic": True,
            "reverse_semantics": "effect backdrives most recent source marker",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        background = background_color(input_grid)
        height = len(input_grid)
        width = len(input_grid[0])
        output = [[background for _ in range(width)] for _ in range(height)]
        for column in range(width):
            active = background
            for row in range(height):
                color = input_grid[row][column]
                if color != background:
                    active = color
                output[row][column] = active
        return tuple(tuple(row) for row in output)


@dataclass(frozen=True)
class EnclosedBackgroundFill:
    """Fill 4-neighbor-enclosed background regions with one learned color."""

    fill_color: int
    name: str = "enclosed_background_fill"
    description_length: int = 4

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "background_topology->output_color",
            "states": ("border_reachable", "enclosed"),
            "forward_deterministic": True,
            "backward_semantics": "fill color certifies enclosed input background",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        background = background_color(input_grid)
        height = len(input_grid)
        width = len(input_grid[0])
        reachable: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = []
        for row in range(height):
            for column in (0, width - 1):
                if input_grid[row][column] == background:
                    stack.append((row, column))
        for column in range(width):
            for row in (0, height - 1):
                if input_grid[row][column] == background:
                    stack.append((row, column))
        while stack:
            row, column = stack.pop()
            if (row, column) in reachable or input_grid[row][column] != background:
                continue
            reachable.add((row, column))
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = row + dr, column + dc
                if 0 <= nr < height and 0 <= nc < width and (nr, nc) not in reachable:
                    stack.append((nr, nc))
        output = [list(row) for row in input_grid]
        for row in range(height):
            for column in range(width):
                if input_grid[row][column] == background and (row, column) not in reachable:
                    output[row][column] = self.fill_color
        return tuple(tuple(row) for row in output)


@dataclass(frozen=True)
class MacroMicroGate:
    """A self-Kronecker callosal interface using macro and micro input coordinates."""

    mode: str
    background: int
    name: str = "macro_micro_gate"
    description_length: int = 4

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "(macro_cell,micro_cell)->output_cell",
            "forward_deterministic": True,
            "backward_may_be_one_to_many": True,
            "mode": self.mode,
            "learned_background": self.background,
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        height = len(input_grid)
        width = len(input_grid[0])
        output: list[list[int]] = []
        for row in range(height * height):
            out_row: list[int] = []
            for column in range(width * width):
                macro = input_grid[row // height][column // width]
                micro = input_grid[row % height][column % width]
                if self.mode == "micro_if_macro_nonbackground":
                    out_row.append(micro if macro != self.background else self.background)
                elif self.mode == "macro_if_micro_nonbackground":
                    out_row.append(macro if micro != self.background else self.background)
                else:
                    raise ValueError(f"unknown macro/micro gate mode: {self.mode}")
            output.append(out_row)
        return tuple(tuple(row) for row in output)


@dataclass(frozen=True)
class RowColumnPermutationCompletion:
    """Complete a square using the intersection of row and column missing-symbol fibers."""

    symbols: tuple[int, ...]
    name: str = "row_column_permutation_completion"
    description_length: int = 5

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "row_missing_symbols intersect column_missing_symbols",
            "symbols": self.symbols,
            "singularity": "commit only singleton intersections; backdrive after each commit",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        background = background_color(input_grid)
        symbol_set = set(self.symbols)
        height = len(input_grid)
        width = len(input_grid[0])
        if height != width or len(self.symbols) != width:
            return tuple(tuple(None for _ in row) for row in input_grid)
        grid: list[list[Optional[int]]] = [
            [None if color == background else color for color in row]
            for row in input_grid
        ]
        changed = True
        while changed:
            changed = False
            for row in range(height):
                for column in range(width):
                    if grid[row][column] is not None:
                        continue
                    row_used = {value for value in grid[row] if value is not None}
                    column_used = {
                        grid[r][column] for r in range(height) if grid[r][column] is not None
                    }
                    candidates = symbol_set - row_used - column_used
                    if len(candidates) == 1:
                        grid[row][column] = next(iter(candidates))
                        changed = True
        return tuple(tuple(row) for row in grid)


def _propose_row_marker_map(training_pairs: Sequence[TrainingPair]) -> Optional[RowMarkerColumnMap]:
    if not training_pairs or not _same_shape(training_pairs):
        return None
    mapping: dict[int, int] = {}
    observed_columns: set[int] = set()
    for input_grid, output_grid in training_pairs:
        background = background_color(input_grid)
        for input_row, output_row in zip(input_grid, output_grid):
            markers = [index for index, color in enumerate(input_row) if color != background]
            if len(markers) != 1 or len(set(output_row)) != 1:
                return None
            column = markers[0]
            output_color = output_row[0]
            prior = mapping.get(column)
            if prior is not None and prior != output_color:
                return None
            mapping[column] = output_color
            observed_columns.add(column)
    if len(observed_columns) < 2:
        return None
    return RowMarkerColumnMap(tuple(sorted(mapping.items())))


def _propose_enclosed_fill(training_pairs: Sequence[TrainingPair]) -> Optional[EnclosedBackgroundFill]:
    if not training_pairs or not _same_shape(training_pairs):
        return None
    fill_color: Optional[int] = None
    saw_change = False
    for input_grid, output_grid in training_pairs:
        background = background_color(input_grid)
        changed: list[tuple[int, int, int]] = []
        for row in range(len(input_grid)):
            for column in range(len(input_grid[0])):
                if input_grid[row][column] == output_grid[row][column]:
                    continue
                if input_grid[row][column] != background:
                    return None
                changed.append((row, column, output_grid[row][column]))
        if not changed:
            continue
        saw_change = True
        colors = {color for _, _, color in changed}
        if len(colors) != 1:
            return None
        candidate_color = next(iter(colors))
        if candidate_color == background:
            return None
        if fill_color is None:
            fill_color = candidate_color
        elif fill_color != candidate_color:
            return None
        candidate = EnclosedBackgroundFill(candidate_color)
        if candidate.predict(input_grid) != output_grid:
            return None
    if not saw_change or fill_color is None:
        return None
    return EnclosedBackgroundFill(fill_color)


def _macro_micro_shape(training_pairs: Sequence[TrainingPair]) -> bool:
    if not training_pairs:
        return False
    return all(
        len(output_grid) == len(input_grid) * len(input_grid)
        and len(output_grid[0]) == len(input_grid[0]) * len(input_grid[0])
        for input_grid, output_grid in training_pairs
    )


def _propose_macro_micro(training_pairs: Sequence[TrainingPair]) -> list[MacroMicroGate]:
    if not _macro_micro_shape(training_pairs):
        return []
    candidate_backgrounds = sorted(
        set.intersection(
            *(
                {color for row in input_grid for color in row}
                for input_grid, _ in training_pairs
            )
        )
    )
    candidates: list[MacroMicroGate] = []
    for background in candidate_backgrounds:
        for mode in ("micro_if_macro_nonbackground", "macro_if_micro_nonbackground"):
            candidate = MacroMicroGate(mode, background)
            if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
                candidates.append(candidate)
    return candidates


def _propose_permutation_completion(
    training_pairs: Sequence[TrainingPair],
) -> Optional[RowColumnPermutationCompletion]:
    if not training_pairs or not _same_shape(training_pairs):
        return None
    learned_symbols: Optional[tuple[int, ...]] = None
    saw_blank = False
    for input_grid, output_grid in training_pairs:
        height = len(output_grid)
        width = len(output_grid[0])
        if height != width:
            return None
        symbols = tuple(sorted(set(output_grid[0])))
        if len(symbols) != width:
            return None
        symbol_set = set(symbols)
        if any(set(row) != symbol_set for row in output_grid):
            return None
        for column in range(width):
            if {output_grid[row][column] for row in range(height)} != symbol_set:
                return None
        if learned_symbols is None:
            learned_symbols = symbols
        elif learned_symbols != symbols:
            return None
        background = background_color(input_grid)
        if background in symbol_set:
            return None
        for row in range(height):
            for column in range(width):
                value = input_grid[row][column]
                if value == background:
                    saw_blank = True
                elif value != output_grid[row][column]:
                    return None
    if learned_symbols is None or not saw_blank:
        return None
    candidate = RowColumnPermutationCompletion(learned_symbols)
    if any(candidate.predict(input_grid) != output_grid for input_grid, output_grid in training_pairs):
        return None
    return candidate


def propose_semantic_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[object]:
    """Propose compact semantic interfaces after lower-level relations fail."""

    if enabled_operator_families is None:
        enabled = frozenset(
            {
                "row_marker_column_to_constant_row",
                "column_downward_propagation",
                "enclosed_background_fill",
                "macro_micro_gate",
                "row_column_permutation_completion",
            }
        )
    else:
        enabled = frozenset(enabled_operator_families)

    candidates: list[object] = []
    if "row_marker_column_to_constant_row" in enabled:
        row_marker = _propose_row_marker_map(training_pairs)
        if row_marker is not None:
            candidates.append(row_marker)
    if "column_downward_propagation" in enabled and _same_shape(training_pairs):
        candidates.append(ColumnDownwardPropagation())
    if "enclosed_background_fill" in enabled:
        enclosed = _propose_enclosed_fill(training_pairs)
        if enclosed is not None:
            candidates.append(enclosed)
    if "macro_micro_gate" in enabled:
        candidates.extend(_propose_macro_micro(training_pairs))
    if "row_column_permutation_completion" in enabled:
        permutation = _propose_permutation_completion(training_pairs)
        if permutation is not None:
            candidates.append(permutation)
    return candidates
