"""Generic object-level ARC hypotheses built on semantic-separator fibers.

These operators deliberately separate three concerns:
1. unitization (connected same-color components),
2. semantic descriptor/rank discovery,
3. a typed transformation (extract one object, or propagate a marker through a
   placeholder component).

When demonstrations leave several equally compact semantic separators alive,
all of them are proposed.  The controller must resolve them only through
prediction singularity; this module does not choose a latent explanation by
lexical accident. No task IDs or held-out targets participate in live inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .callosal_separator import (
    SemanticObservation,
    SeparatorModel,
    learn_minimal_separator_fiber,
)
from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color


@dataclass(frozen=True)
class _Component:
    color: int
    cells: frozenset[tuple[int, int]]

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        rows = [r for r, _ in self.cells]
        cols = [c for _, c in self.cells]
        return min(rows), min(cols), max(rows), max(cols)

    @property
    def area(self) -> int:
        return len(self.cells)

    @property
    def height(self) -> int:
        r0, _, r1, _ = self.bbox
        return r1 - r0 + 1

    @property
    def width(self) -> int:
        _, c0, _, c1 = self.bbox
        return c1 - c0 + 1

    @property
    def bbox_area(self) -> int:
        return self.height * self.width

    @property
    def density_key(self) -> tuple[int, int]:
        return self.area, self.bbox_area


def _components(grid: Grid, *, include_background: bool = False) -> tuple[_Component, ...]:
    bg = background_color(grid)
    h, w = len(grid), len(grid[0])
    seen: set[tuple[int, int]] = set()
    result: list[_Component] = []
    for row in range(h):
        for col in range(w):
            if (row, col) in seen:
                continue
            color = grid[row][col]
            if not include_background and color == bg:
                continue
            stack = [(row, col)]
            seen.add((row, col))
            cells: set[tuple[int, int]] = set()
            while stack:
                r, c = stack.pop()
                cells.add((r, c))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if (
                        0 <= nr < h
                        and 0 <= nc < w
                        and (nr, nc) not in seen
                        and grid[nr][nc] == color
                    ):
                        seen.add((nr, nc))
                        stack.append((nr, nc))
            result.append(_Component(color, frozenset(cells)))
    return tuple(result)


def _crop(grid: Grid, component: _Component) -> Grid:
    r0, c0, r1, c1 = component.bbox
    return tuple(tuple(grid[r][c0 : c1 + 1]) for r in range(r0, r1 + 1))


def _rank(values: list[object], index: int, reverse: bool = False) -> int:
    order = sorted(range(len(values)), key=lambda i: (values[i], i), reverse=reverse)
    return order.index(index)


def _component_descriptors(components: Sequence[_Component], index: int) -> dict[str, object]:
    comp = components[index]
    areas = [item.area for item in components]
    heights = [item.height for item in components]
    widths = [item.width for item in components]
    bbox_areas = [item.bbox_area for item in components]
    densities = [item.density_key for item in components]
    color_counts: dict[int, int] = {}
    for item in components:
        color_counts[item.color] = color_counts.get(item.color, 0) + 1
    return {
        "color": comp.color,
        "area": comp.area,
        "height": comp.height,
        "width": comp.width,
        "bbox_area": comp.bbox_area,
        "density_key": comp.density_key,
        "is_min_area": comp.area == min(areas),
        "is_max_area": comp.area == max(areas),
        "is_unique_area": areas.count(comp.area) == 1,
        "area_rank_asc": _rank(areas, index),
        "area_rank_desc": _rank(areas, index, reverse=True),
        "height_rank_asc": _rank(heights, index),
        "width_rank_asc": _rank(widths, index),
        "bbox_area_rank_asc": _rank(bbox_areas, index),
        "density_rank_asc": _rank(densities, index),
        "same_color_component_count": color_counts[comp.color],
    }


@dataclass(frozen=True)
class ComponentSelectExtract:
    separator: SeparatorModel
    description_length: int = 5

    @property
    def name(self) -> str:
        fields = "+".join(self.separator.descriptor_names)
        return f"component_select_extract[{fields}]"

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "component_descriptors<->selected_for_bbox_extraction",
            "separator": self.separator.callosal_summary,
            "transform": "emit selected component bounding-box crop",
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        components = _components(input_grid)
        selected: list[_Component] = []
        for index, component in enumerate(components):
            decision = self.separator.predict(_component_descriptors(components, index))
            if decision is True:
                selected.append(component)
            elif decision is None:
                return None
        if not selected:
            return None
        crops = [_crop(input_grid, component) for component in selected]
        if any(crop != crops[0] for crop in crops[1:]):
            return None
        return crops[0]


def propose_component_extract_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[ComponentSelectExtract]:
    if enabled_operator_families is not None and "component_select_extract" not in enabled_operator_families:
        return []
    if not training_pairs:
        return []

    observations: list[SemanticObservation] = []
    for input_grid, output_grid in training_pairs:
        components = _components(input_grid)
        if len(components) < 2:
            return []
        matching = [index for index, component in enumerate(components) if _crop(input_grid, component) == output_grid]
        if not matching:
            return []
        for index, _ in enumerate(components):
            observations.append(
                SemanticObservation(
                    _component_descriptors(components, index), index in matching
                )
            )

    separators = learn_minimal_separator_fiber(
        observations,
        (
            "color",
            "area",
            "height",
            "width",
            "bbox_area",
            "density_key",
            "is_min_area",
            "is_max_area",
            "is_unique_area",
            "area_rank_asc",
            "area_rank_desc",
            "height_rank_asc",
            "width_rank_asc",
            "bbox_area_rank_asc",
            "density_rank_asc",
            "same_color_component_count",
        ),
        max_arity=2,
    )
    candidates = [ComponentSelectExtract(separator) for separator in separators]
    return [
        candidate
        for candidate in candidates
        if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs)
    ]


def _component_neighbors(grid: Grid, component: _Component) -> set[int]:
    h, w = len(grid), len(grid[0])
    result: set[int] = set()
    for r, c in component.cells:
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in component.cells:
                result.add(grid[nr][nc])
    return result


@dataclass(frozen=True)
class UniqueNeighborComponentPropagation:
    placeholder_color: int
    name: str = "unique_neighbor_component_propagation"
    description_length: int = 4

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "unique_adjacent_marker_color<->placeholder_component_effect",
            "placeholder_color": self.placeholder_color,
            "forward_deterministic": True,
            "backward_semantics": "uniform recolor identifies the unique incident marker color",
        }

    def predict(self, input_grid: Grid) -> PartialGrid:
        bg = background_color(input_grid)
        output = [list(row) for row in input_grid]
        placeholder_components = [
            component
            for component in _components(input_grid, include_background=True)
            if component.color == self.placeholder_color
        ]
        for component in placeholder_components:
            markers = {
                color
                for color in _component_neighbors(input_grid, component)
                if color not in {bg, self.placeholder_color}
            }
            if len(markers) != 1:
                continue
            color = next(iter(markers))
            for row, col in component.cells:
                output[row][col] = color
        return tuple(tuple(row) for row in output)


def propose_unique_neighbor_propagation_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[UniqueNeighborComponentPropagation]:
    if enabled_operator_families is not None and "unique_neighbor_component_propagation" not in enabled_operator_families:
        return []
    if not training_pairs:
        return []
    if any(
        len(input_grid) != len(output_grid)
        or len(input_grid[0]) != len(output_grid[0])
        for input_grid, output_grid in training_pairs
    ):
        return []

    before_colors = {
        input_grid[r][c]
        for input_grid, output_grid in training_pairs
        for r in range(len(input_grid))
        for c in range(len(input_grid[0]))
        if input_grid[r][c] != output_grid[r][c]
    }
    if len(before_colors) != 1:
        return []
    placeholder = next(iter(before_colors))
    candidate = UniqueNeighborComponentPropagation(placeholder)
    if all(candidate.predict(input_grid) == output_grid for input_grid, output_grid in training_pairs):
        return [candidate]
    return []


def propose_generic_object_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
):
    return [
        *propose_component_extract_hypotheses(training_pairs, enabled_operator_families),
        *propose_unique_neighbor_propagation_hypotheses(training_pairs, enabled_operator_families),
    ]
