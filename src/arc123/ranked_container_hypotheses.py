"""Ranked container transformations controlled by a compact legend count.

This family was introduced after the simpler ``unique_neighbor_component``
hypothesis was falsified on opened ARC2 development task 97d7923e.

Generic structure:

* a *container* is a vertical segment with equal nonzero endpoint colors and a
  nonzero, constant, different interior color;
* free pixels of an endpoint color that are not used by any container form the
  legend for that color;
* the legend cardinality r is interpreted as a 1-based rank;
* containers of the same endpoint color are ordered by interior length,
  longest first;
* the r-th container has its interior recolored to its endpoint color.

The rule is inferred from training evidence and applied without task IDs or
held-out outputs.  If a test color has an unsupported/invalid rank, prediction
remains UNKNOWN rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color


@dataclass(frozen=True)
class VerticalContainer:
    column: int
    top: int
    bottom: int
    endpoint_color: int
    interior_color: int

    @property
    def interior_length(self) -> int:
        return self.bottom - self.top - 1

    @property
    def endpoint_cells(self) -> frozenset[tuple[int, int]]:
        return frozenset(((self.top, self.column), (self.bottom, self.column)))

    @property
    def interior_cells(self) -> frozenset[tuple[int, int]]:
        return frozenset(
            (row, self.column) for row in range(self.top + 1, self.bottom)
        )


def _containers(grid: Grid) -> tuple[VerticalContainer, ...]:
    """Detect maximal simple vertical endpoint/interior containers.

    For each column and endpoint color, consider consecutive occurrences of the
    endpoint color.  A candidate is accepted when the open interval is at
    least one cell long and is filled by one constant nonzero, different color.
    Consecutive endpoint occurrences avoid inventing a larger container across
    a nested same-color endpoint.
    """

    bg = background_color(grid)
    height = len(grid)
    width = len(grid[0])
    result: list[VerticalContainer] = []
    for column in range(width):
        by_color: dict[int, list[int]] = {}
        for row in range(height):
            color = grid[row][column]
            if color == bg:
                continue
            by_color.setdefault(color, []).append(row)
        for endpoint_color, rows in by_color.items():
            for top, bottom in zip(rows, rows[1:]):
                if bottom - top < 2:
                    continue
                interior = [grid[row][column] for row in range(top + 1, bottom)]
                if not interior or len(set(interior)) != 1:
                    continue
                interior_color = interior[0]
                if interior_color in {bg, endpoint_color}:
                    continue
                result.append(
                    VerticalContainer(
                        column=column,
                        top=top,
                        bottom=bottom,
                        endpoint_color=endpoint_color,
                        interior_color=interior_color,
                    )
                )
    return tuple(result)


def _legend_count(grid: Grid, endpoint_color: int, containers: Sequence[VerticalContainer]) -> int:
    used_endpoints = set().union(
        *(
            container.endpoint_cells
            for container in containers
            if container.endpoint_color == endpoint_color
        )
    ) if containers else set()
    return sum(
        1
        for row, values in enumerate(grid)
        for column, color in enumerate(values)
        if color == endpoint_color and (row, column) not in used_endpoints
    )


def _ranked_for_color(
    containers: Sequence[VerticalContainer], endpoint_color: int
) -> tuple[VerticalContainer, ...]:
    relevant = [
        container for container in containers if container.endpoint_color == endpoint_color
    ]
    # Equal lengths make rank ambiguous.  Keep deterministic coordinate order
    # only so validation can reject training sets that rely on such a tie.
    return tuple(
        sorted(
            relevant,
            key=lambda container: (
                -container.interior_length,
                container.column,
                container.top,
            ),
        )
    )


@dataclass(frozen=True)
class LegendCountRankedContainerFill:
    """Legend cardinality selects a length-ranked container for each color."""

    name: str = "legend_count_ranked_container_fill"
    description_length: int = 7

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "legend_count(endpoint_color)<->container_length_rank<->interior_effect",
            "rank_order": "interior_length_descending_1_based",
            "effect": "recolor selected container interior to endpoint color",
            "forward_deterministic": True,
            "backward_semantics": "observed recolored container identifies the rank encoded by the legend count",
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        containers = _containers(input_grid)
        if not containers:
            return None
        output = [list(row) for row in input_grid]
        endpoint_colors = sorted({container.endpoint_color for container in containers})
        made_selection = False
        for endpoint_color in endpoint_colors:
            ranked = _ranked_for_color(containers, endpoint_color)
            lengths = [container.interior_length for container in ranked]
            # Ranking is semantically undefined if equal lengths straddle a
            # possible selected position.
            if len(lengths) != len(set(lengths)):
                return None
            rank = _legend_count(input_grid, endpoint_color, containers)
            if rank == 0:
                # A color can occur in containers without participating in this
                # legend-controlled family; leave it untouched.
                continue
            if rank > len(ranked):
                return None
            selected = ranked[rank - 1]
            for row, column in selected.interior_cells:
                output[row][column] = endpoint_color
            made_selection = True
        return tuple(tuple(row) for row in output) if made_selection else None


def _training_relation_is_exact(
    candidate: LegendCountRankedContainerFill,
    training_pairs: Sequence[TrainingPair],
) -> bool:
    """Require every demonstrated change to be exactly explained by the rank rule."""

    for input_grid, output_grid in training_pairs:
        prediction = candidate.predict(input_grid)
        if prediction is None or prediction != output_grid:
            return False
    return True


def propose_ranked_container_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[LegendCountRankedContainerFill]:
    if enabled_operator_families is not None and (
        "legend_count_ranked_container_fill" not in enabled_operator_families
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
    candidate = LegendCountRankedContainerFill()
    return [candidate] if _training_relation_is_exact(candidate, training_pairs) else []
