"""Typed compositional program synthesis for ARC Forward–Backward Singularity Learning.

This module is deliberately different from the task-shaped proposer catalogue.
It defines a small reusable typed grammar and enumerates *compositions* of
primitives.  No primitive below names an ARC task or a complete ARC rule.

The first milestone supports unary semantic pipelines of the form

    Grid -> semantic value -> ... -> Grid

where a primitive may read the original input grid as immutable rendering
context.  The synthesizer evaluates every complete program against every
training demonstration and returns the full minimum-cost exact program fiber.
It never ranks on only the first demonstration and never sees held-out targets.

This is intentionally a small first IR.  It is enough to synthesize programs
such as

    components4 -> count -> add1 -> render_background_column

and

    components4 -> select_unique_area -> crop_bbox

from independently reusable primitives.  Later milestones can generalize the
IR from unary pipelines to typed DAGs/branching programs without changing the
compatibility contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import Component, background_color, connected_components


class SemanticType(str, Enum):
    GRID = "Grid"
    COMPONENTS = "Components"
    COMPONENT = "Component"
    INT = "Int"


SemanticValue = Grid | tuple[Component, ...] | Component | int
PrimitiveFn = Callable[[SemanticValue, Grid], Optional[SemanticValue]]


@dataclass(frozen=True)
class Primitive:
    """One typed reusable semantic operation."""

    name: str
    input_type: SemanticType
    output_type: SemanticType
    cost: int
    fn: PrimitiveFn

    def apply(self, value: SemanticValue, root_grid: Grid) -> Optional[SemanticValue]:
        return self.fn(value, root_grid)


@dataclass(frozen=True)
class TypedProgram:
    """A type-correct unary semantic pipeline."""

    steps: tuple[Primitive, ...]

    @property
    def name(self) -> str:
        return "synth[" + " -> ".join(step.name for step in self.steps) + "]"

    @property
    def description_length(self) -> int:
        return sum(step.cost for step in self.steps)

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "typed_compositional_program",
            "steps": tuple(step.name for step in self.steps),
            "cost": self.description_length,
            "generated_not_task_dispatched": True,
        }

    def execute(self, input_grid: Grid) -> Optional[SemanticValue]:
        value: SemanticValue = input_grid
        current_type = SemanticType.GRID
        for step in self.steps:
            if step.input_type is not current_type:
                return None
            value = step.apply(value, input_grid)
            if value is None:
                return None
            current_type = step.output_type
        return value

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        if not self.steps or self.steps[-1].output_type is not SemanticType.GRID:
            return None
        value = self.execute(input_grid)
        if value is None or not isinstance(value, tuple):
            return None
        return value  # type: ignore[return-value]


def _components4(value: SemanticValue, _root: Grid) -> Optional[SemanticValue]:
    if not isinstance(value, tuple):
        return None
    grid = value  # type: ignore[assignment]
    components = connected_components(grid, connectivity=4)
    return components if components else None


def _components8(value: SemanticValue, _root: Grid) -> Optional[SemanticValue]:
    if not isinstance(value, tuple):
        return None
    grid = value  # type: ignore[assignment]
    components = connected_components(grid, connectivity=8)
    return components if components else None


def _count(value: SemanticValue, _root: Grid) -> Optional[SemanticValue]:
    if not isinstance(value, tuple):
        return None
    return len(value)


def _add1(value: SemanticValue, _root: Grid) -> Optional[SemanticValue]:
    return value + 1 if isinstance(value, int) else None


def _component_tuple(value: SemanticValue) -> Optional[tuple[Component, ...]]:
    if not isinstance(value, tuple) or not value:
        return None
    if not all(isinstance(item, Component) for item in value):
        return None
    return tuple(value)  # type: ignore[return-value]


def _select_unique_area(value: SemanticValue, _root: Grid) -> Optional[SemanticValue]:
    components = _component_tuple(value)
    if components is None:
        return None
    multiplicity: dict[int, int] = {}
    for component in components:
        multiplicity[component.area] = multiplicity.get(component.area, 0) + 1
    selected = [component for component in components if multiplicity[component.area] == 1]
    return selected[0] if len(selected) == 1 else None


def _select_unique_min_area(value: SemanticValue, _root: Grid) -> Optional[SemanticValue]:
    components = _component_tuple(value)
    if components is None:
        return None
    minimum = min(component.area for component in components)
    selected = [component for component in components if component.area == minimum]
    return selected[0] if len(selected) == 1 else None


def _select_unique_max_area(value: SemanticValue, _root: Grid) -> Optional[SemanticValue]:
    components = _component_tuple(value)
    if components is None:
        return None
    maximum = max(component.area for component in components)
    selected = [component for component in components if component.area == maximum]
    return selected[0] if len(selected) == 1 else None


def _crop_bbox(value: SemanticValue, root: Grid) -> Optional[SemanticValue]:
    if not isinstance(value, Component):
        return None
    r0, c0, r1, c1 = value.bbox
    return tuple(tuple(root[row][c0 : c1 + 1]) for row in range(r0, r1 + 1))


def _render_background_column(value: SemanticValue, root: Grid) -> Optional[SemanticValue]:
    if not isinstance(value, int) or value < 1:
        return None
    background = background_color(root)
    return tuple((background,) for _ in range(value))


DEFAULT_SYNTHESIS_PRIMITIVES: tuple[Primitive, ...] = (
    Primitive("components4", SemanticType.GRID, SemanticType.COMPONENTS, 1, _components4),
    Primitive("components8", SemanticType.GRID, SemanticType.COMPONENTS, 1, _components8),
    Primitive("count", SemanticType.COMPONENTS, SemanticType.INT, 1, _count),
    Primitive("add1", SemanticType.INT, SemanticType.INT, 1, _add1),
    Primitive(
        "select_unique_area",
        SemanticType.COMPONENTS,
        SemanticType.COMPONENT,
        1,
        _select_unique_area,
    ),
    Primitive(
        "select_unique_min_area",
        SemanticType.COMPONENTS,
        SemanticType.COMPONENT,
        1,
        _select_unique_min_area,
    ),
    Primitive(
        "select_unique_max_area",
        SemanticType.COMPONENTS,
        SemanticType.COMPONENT,
        1,
        _select_unique_max_area,
    ),
    Primitive("crop_bbox", SemanticType.COMPONENT, SemanticType.GRID, 1, _crop_bbox),
    Primitive(
        "render_background_column",
        SemanticType.INT,
        SemanticType.GRID,
        1,
        _render_background_column,
    ),
)


@dataclass(frozen=True)
class SynthesisResult:
    programs: tuple[TypedProgram, ...]
    generated_complete_program_count: int
    exact_program_count: int
    minimum_exact_cost: Optional[int]


def enumerate_typed_programs(
    primitives: Sequence[Primitive] = DEFAULT_SYNTHESIS_PRIMITIVES,
    *,
    max_steps: int = 5,
    max_cost: int = 6,
) -> tuple[TypedProgram, ...]:
    """Enumerate type-correct Grid->Grid programs to bounded depth/cost.

    Grid outputs terminate a program.  This avoids trivial cycles in the first
    unary-pipeline IR and makes the search finite without task-dependent
    heuristics.
    """

    if max_steps < 1 or max_cost < 1:
        return ()
    frontier: list[tuple[tuple[Primitive, ...], SemanticType, int]] = [
        ((), SemanticType.GRID, 0)
    ]
    complete: list[TypedProgram] = []
    for _depth in range(max_steps):
        next_frontier: list[tuple[tuple[Primitive, ...], SemanticType, int]] = []
        for steps, current_type, current_cost in frontier:
            for primitive in primitives:
                if primitive.input_type is not current_type:
                    continue
                new_cost = current_cost + primitive.cost
                if new_cost > max_cost:
                    continue
                new_steps = (*steps, primitive)
                if primitive.output_type is SemanticType.GRID:
                    if new_steps:
                        complete.append(TypedProgram(new_steps))
                    continue
                next_frontier.append((new_steps, primitive.output_type, new_cost))
        frontier = next_frontier
        if not frontier:
            break
    return tuple(
        sorted(
            complete,
            key=lambda program: (program.description_length, len(program.steps), program.name),
        )
    )


def synthesize_exact_program_fiber(
    training_pairs: Sequence[TrainingPair],
    primitives: Sequence[Primitive] = DEFAULT_SYNTHESIS_PRIMITIVES,
    *,
    max_steps: int = 5,
    max_cost: int = 6,
) -> SynthesisResult:
    """Return the full minimum-cost exact program fiber on all demonstrations."""

    if not training_pairs:
        return SynthesisResult((), 0, 0, None)
    generated = enumerate_typed_programs(
        primitives,
        max_steps=max_steps,
        max_cost=max_cost,
    )
    exact = [
        program
        for program in generated
        if all(
            program.predict(input_grid) == output_grid
            for input_grid, output_grid in training_pairs
        )
    ]
    if not exact:
        return SynthesisResult((), len(generated), 0, None)
    minimum_cost = min(program.description_length for program in exact)
    fiber = tuple(
        program
        for program in exact
        if program.description_length == minimum_cost
    )
    return SynthesisResult(fiber, len(generated), len(exact), minimum_cost)


def propose_typed_synthesized_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[TypedProgram]:
    """Controller adapter for the bounded typed synthesizer."""

    if enabled_operator_families is not None and "typed_program_synthesis" not in enabled_operator_families:
        return []
    return list(synthesize_exact_program_fiber(training_pairs).programs)
