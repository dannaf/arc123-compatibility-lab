"""Reusable ARC semantic primitives for observationally quotiented synthesis.

The vocabulary is intentionally factorized: unitizers, measurements, selectors,
arithmetic and renderers are independent primitives. Complete ARC task names do
not appear here.

Terminal renderers also expose exact finite backward-preimage relations where
available.  These relations use only an input grid and an observed *training*
output. They are the backward view of the same local semantic relation as the
forward renderer and can therefore be used for controlled F/B search pruning
without changing the hypothesis language.
"""

from __future__ import annotations

from typing import Optional

from .model import Grid
from .observational_program_synthesis import NaryPrimitive, SemanticValue
from .perceptions import Component, background_color, connected_components
from .segment_hypotheses import _render_equalized, _segments


GRID = "Grid"
COMPONENTS = "Components"
COMPONENT = "Component"
INT = "Int"
INT_SEQUENCE = "IntSequence"


def _only(args: tuple[SemanticValue, ...]) -> Optional[SemanticValue]:
    return args[0] if len(args) == 1 else None


def components4(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    if not isinstance(value, tuple):
        return None
    result = connected_components(value, connectivity=4)  # type: ignore[arg-type]
    return result or None


def components8(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    if not isinstance(value, tuple):
        return None
    result = connected_components(value, connectivity=8)  # type: ignore[arg-type]
    return result or None


def count(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    return len(value) if isinstance(value, tuple) else None


def add1(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    return value + 1 if isinstance(value, int) else None


def add_ints(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    if len(args) != 2 or not all(isinstance(value, int) for value in args):
        return None
    return int(args[0]) + int(args[1])


def ceil_half(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    return (value + 1) // 2 if isinstance(value, int) else None


def _component_tuple(value: SemanticValue) -> Optional[tuple[Component, ...]]:
    if not isinstance(value, tuple) or not value:
        return None
    if not all(isinstance(item, Component) for item in value):
        return None
    return tuple(value)  # type: ignore[return-value]


def select_unique_area(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    components = _component_tuple(_only(args))
    if components is None:
        return None
    multiplicity: dict[int, int] = {}
    for component in components:
        multiplicity[component.area] = multiplicity.get(component.area, 0) + 1
    selected = [component for component in components if multiplicity[component.area] == 1]
    return selected[0] if len(selected) == 1 else None


def crop_bbox(args: tuple[SemanticValue, ...], root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    if not isinstance(value, Component):
        return None
    r0, c0, r1, c1 = value.bbox
    return tuple(tuple(root[row][c0 : c1 + 1]) for row in range(r0, r1 + 1))


def backward_crop_bbox(
    root: Grid, target: Grid
) -> Optional[tuple[tuple[SemanticValue, ...], ...]]:
    """All 4/8-connected root components whose forward crop is the target."""

    candidates: dict[tuple[int, tuple[tuple[int, int], ...], tuple[int, int, int, int]], Component] = {}
    for connectivity in (4, 8):
        for component in connected_components(root, connectivity=connectivity):
            key = (component.color, component.cells, component.bbox)
            candidates.setdefault(key, component)
    return tuple(
        (component,)
        for component in candidates.values()
        if crop_bbox((component,), root) == target
    )


def render_background_column(args: tuple[SemanticValue, ...], root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    if not isinstance(value, int) or value < 1:
        return None
    background = background_color(root)
    return tuple((background,) for _ in range(value))


def backward_render_background_column(
    root: Grid, target: Grid
) -> Optional[tuple[tuple[SemanticValue, ...], ...]]:
    if not target:
        return ()
    background = background_color(root)
    if any(len(row) != 1 or row[0] != background for row in target):
        return ()
    return ((len(target),),)


def segment_lengths(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    if not isinstance(value, tuple):
        return None
    segments = _segments(value)  # type: ignore[arg-type]
    if segments is None:
        return None
    return tuple(len(cells) for _, cells, _ in segments)


def sequence_min(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    return min(value) if isinstance(value, tuple) and value and all(isinstance(x, int) for x in value) else None


def sequence_max(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    return max(value) if isinstance(value, tuple) and value and all(isinstance(x, int) for x in value) else None


def sequence_second_desc(args: tuple[SemanticValue, ...], _root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    if not isinstance(value, tuple) or len(value) < 2 or not all(isinstance(x, int) for x in value):
        return None
    return sorted(value, reverse=True)[1]


def equalize_segments(args: tuple[SemanticValue, ...], root: Grid) -> Optional[SemanticValue]:
    value = _only(args)
    return _render_equalized(root, value) if isinstance(value, int) else None


def backward_equalize_segments(
    root: Grid, target: Grid
) -> Optional[tuple[tuple[SemanticValue, ...], ...]]:
    """Infer the unique common target extent when the output is in this renderer's image."""

    output_segments = _segments(target)
    if output_segments is None:
        return ()
    lengths = {len(cells) for _, cells, _ in output_segments}
    if len(lengths) != 1:
        return ()
    target_length = next(iter(lengths))
    if _render_equalized(root, target_length) != target:
        return ()
    return ((target_length,),)


DEFAULT_OBSERVATIONAL_ARC_PRIMITIVES: tuple[NaryPrimitive, ...] = (
    NaryPrimitive("components4", (GRID,), COMPONENTS, 1, components4),
    NaryPrimitive("components8", (GRID,), COMPONENTS, 1, components8),
    NaryPrimitive("count", (COMPONENTS,), INT, 1, count),
    NaryPrimitive("add1", (INT,), INT, 1, add1),
    NaryPrimitive("select_unique_area", (COMPONENTS,), COMPONENT, 1, select_unique_area),
    NaryPrimitive(
        "crop_bbox",
        (COMPONENT,),
        GRID,
        1,
        crop_bbox,
        backward_preimage=backward_crop_bbox,
    ),
    NaryPrimitive(
        "render_background_column",
        (INT,),
        GRID,
        1,
        render_background_column,
        backward_preimage=backward_render_background_column,
    ),
    NaryPrimitive("segment_lengths", (GRID,), INT_SEQUENCE, 1, segment_lengths),
    NaryPrimitive("sequence_min", (INT_SEQUENCE,), INT, 1, sequence_min),
    NaryPrimitive("sequence_max", (INT_SEQUENCE,), INT, 1, sequence_max),
    NaryPrimitive("sequence_second_desc", (INT_SEQUENCE,), INT, 1, sequence_second_desc),
    NaryPrimitive("add_ints", (INT, INT), INT, 1, add_ints),
    NaryPrimitive("ceil_half", (INT,), INT, 1, ceil_half),
    NaryPrimitive(
        "equalize_segments",
        (INT,),
        GRID,
        1,
        equalize_segments,
        backward_preimage=backward_equalize_segments,
    ),
)


DEFAULT_TERMINAL_RENDERERS: tuple[str, ...] = (
    "crop_bbox",
    "render_background_column",
    "equalize_segments",
)
