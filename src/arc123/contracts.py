"""Benchmark-neutral contracts shared by static ARC12 and external ARC3 worlds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from .model import ActionKind, Counterexample, SupportState


@dataclass(frozen=True)
class EvidenceObservation:
    """An observable fact supplied by a benchmark adapter, never an oracle answer."""

    observation_id: str
    world_id: str
    observation_kind: str
    payload: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "world_id": self.world_id,
            "observation_kind": self.observation_kind,
            "payload": dict(self.payload),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class HypothesisAction:
    """A theory transformation with explicit parameters and provenance."""

    kind: ActionKind
    target: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "target": self.target,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class EnvironmentAction:
    """An adapter-specific action whose outcome is observed through one contract."""

    action_type: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"action_type": self.action_type, "parameters": dict(self.parameters)}


@dataclass(frozen=True)
class TransitionFeedback:
    """Observable result of an internal evidence query or external environment probe."""

    action: EnvironmentAction
    before: EvidenceObservation
    after: EvidenceObservation
    accepted: bool
    changed: bool | None
    progress: float | None
    terminal: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.as_dict(),
            "before": self.before.as_dict(),
            "after": self.after.as_dict(),
            "accepted": self.accepted,
            "changed": self.changed,
            "progress": self.progress,
            "terminal": self.terminal,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CompatibilitySupport:
    """Observed support for one prediction, preserving UNKNOWN separately from zero support."""

    observation_id: str
    support_state: SupportState
    asserted_cell_count: int
    matching_cell_count: int
    contradiction_count: int
    unknown_cell_count: int
    counterexamples: tuple[Counterexample, ...] = ()

    @property
    def exact_support_zero(self) -> bool:
        return self.support_state is SupportState.IMPOSSIBLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "support_state": self.support_state.value,
            "asserted_cell_count": self.asserted_cell_count,
            "matching_cell_count": self.matching_cell_count,
            "contradiction_count": self.contradiction_count,
            "unknown_cell_count": self.unknown_cell_count,
            "exact_support_zero": self.exact_support_zero,
            "counterexamples": [item.as_dict() for item in self.counterexamples],
        }


@dataclass(frozen=True)
class Residual:
    """A concrete unexplained or contradictory region, not a trace-only label."""

    observation_id: str
    residual_kind: str
    cells: tuple[tuple[int, int], ...]
    predicted_values: tuple[int | None, ...] = ()
    observed_values: tuple[int, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "residual_kind": self.residual_kind,
            "cell_count": len(self.cells),
            "cells": [list(cell) for cell in self.cells],
            "predicted_values": list(self.predicted_values),
            "observed_values": list(self.observed_values),
        }


class ObservationWorld(Protocol):
    """Benchmark-neutral observation/action boundary used by all adapters."""

    def observe(self) -> EvidenceObservation: ...

    def available_actions(self) -> Sequence[EnvironmentAction]: ...

    def act(self, action: EnvironmentAction) -> TransitionFeedback: ...
