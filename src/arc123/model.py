"""Shared, observable data model for ARC123 iterative hypothesis learning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional, Sequence


Grid = tuple[tuple[int, ...], ...]
PartialGrid = tuple[tuple[Optional[int], ...], ...]
TrainingPair = tuple[Grid, Grid]


class ActionKind(str, Enum):
    ATTEND = "ATTEND"
    PROPOSE = "PROPOSE"
    APPLY_HYPOTHESIS = "APPLY_HYPOTHESIS"
    COMPARE = "COMPARE"
    FIND_COUNTEREXAMPLE = "FIND_COUNTEREXAMPLE"
    SPECIALIZE = "SPECIALIZE"
    GENERALIZE = "GENERALIZE"
    COMPOSE = "COMPOSE"
    SPLIT_SCOPE = "SPLIT_SCOPE"
    MERGE_RULES = "MERGE_RULES"
    REJECT_HYPOTHESIS = "REJECT_HYPOTHESIS"
    PROMOTE_CONSTRAINT = "PROMOTE_CONSTRAINT"
    COMMIT = "COMMIT"


class SupportState(str, Enum):
    UNKNOWN = "UNKNOWN"
    COMPATIBLE = "COMPATIBLE"
    IMPOSSIBLE = "IMPOSSIBLE"


def grid_from(value: Sequence[Sequence[int]], label: str = "grid") -> Grid:
    if not isinstance(value, Sequence) or not value:
        raise ValueError(f"{label} must be a non-empty grid")
    width: Optional[int] = None
    rows: list[tuple[int, ...]] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, Sequence) or not row:
            raise ValueError(f"{label}[{row_index}] must be a non-empty row")
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ValueError(f"{label} must be rectangular")
        if not all(isinstance(cell, int) for cell in row):
            raise ValueError(f"{label}[{row_index}] must contain integer colors")
        rows.append(tuple(row))
    return tuple(rows)


def grid_to_lists(grid: Grid | PartialGrid) -> list[list[Optional[int]]]:
    return [list(row) for row in grid]


def grid_shape(grid: Grid | PartialGrid) -> tuple[int, int]:
    return len(grid), len(grid[0])


@dataclass(frozen=True)
class Counterexample:
    demo_index: int
    row: int
    column: int
    predicted: int
    observed: int

    def as_dict(self) -> dict[str, int]:
        return {
            "demo_index": self.demo_index,
            "row": self.row,
            "column": self.column,
            "predicted": self.predicted,
            "observed": self.observed,
        }


@dataclass(frozen=True)
class CompatibilityFeedback:
    demo_index: int
    asserted_cell_count: int
    matching_cell_count: int
    contradiction_count: int
    unknown_cell_count: int
    support_state: SupportState
    counterexamples: tuple[Counterexample, ...]

    @property
    def exact_support_zero(self) -> bool:
        return self.support_state is SupportState.IMPOSSIBLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "demo_index": self.demo_index,
            "asserted_cell_count": self.asserted_cell_count,
            "matching_cell_count": self.matching_cell_count,
            "contradiction_count": self.contradiction_count,
            "unknown_cell_count": self.unknown_cell_count,
            "support_state": self.support_state.value,
            "exact_support_zero": self.exact_support_zero,
            "counterexamples": [item.as_dict() for item in self.counterexamples],
        }


@dataclass(frozen=True)
class HypothesisAssessment:
    hypothesis_name: str
    description_length: int
    feedback: tuple[CompatibilityFeedback, ...]

    @property
    def matching_cell_count(self) -> int:
        return sum(item.matching_cell_count for item in self.feedback)

    @property
    def contradiction_count(self) -> int:
        return sum(item.contradiction_count for item in self.feedback)

    @property
    def unknown_cell_count(self) -> int:
        return sum(item.unknown_cell_count for item in self.feedback)

    @property
    def asserted_cell_count(self) -> int:
        return sum(item.asserted_cell_count for item in self.feedback)

    @property
    def is_training_exact(self) -> bool:
        return self.contradiction_count == 0 and self.unknown_cell_count == 0

    @property
    def is_partial_compatible(self) -> bool:
        return (
            self.contradiction_count == 0
            and self.matching_cell_count > 0
            and self.unknown_cell_count > 0
        )

    @property
    def first_counterexample(self) -> Optional[Counterexample]:
        for item in self.feedback:
            if item.counterexamples:
                return item.counterexamples[0]
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "hypothesis": self.hypothesis_name,
            "description_length": self.description_length,
            "matching_cell_count": self.matching_cell_count,
            "contradiction_count": self.contradiction_count,
            "unknown_cell_count": self.unknown_cell_count,
            "is_training_exact": self.is_training_exact,
            "is_partial_compatible": self.is_partial_compatible,
            "feedback": [item.as_dict() for item in self.feedback],
        }


@dataclass(frozen=True)
class SolveResult:
    predictions: tuple[Grid, ...]
    selected_hypothesis: str
    training_exact: bool
    used_fallback: bool
    posterior_mass: float
    trace: Mapping[str, Any]
