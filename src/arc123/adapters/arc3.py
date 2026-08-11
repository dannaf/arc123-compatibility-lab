"""Common ARC3 adapter contract for future external-action integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class ExternalTransition:
    observation: Mapping[str, Any]
    progress: float | None
    terminal: bool


class ARC3Environment(Protocol):
    """The shared core uses this interface without assuming official ARC3 semantics."""

    def observe(self) -> Mapping[str, Any]: ...

    def act(self, action: Mapping[str, Any]) -> ExternalTransition: ...
