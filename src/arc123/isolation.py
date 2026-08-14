"""Hard boundaries between live adapters and offline oracle/debug artifacts."""

from __future__ import annotations

from pathlib import PurePosixPath


class OracleIsolationError(ValueError):
    """Raised when a live adapter is asked to load an offline oracle/debug artifact."""


_FORBIDDEN_LIVE_PATH_TOKENS = (
    "oracle",
    "brain_surgery",
    "brainsurgery",
    "reasoning",
    "rule_phase",
    "offline_diff",
    "decomposition",
    "feature",
    "gt_",
)


def require_public_arc3_transition_path(path: str) -> PurePosixPath:
    """Allow only source-pinned observable human-play segments in a live ARC3 replay."""

    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise OracleIsolationError("ARC3 live transition path must be repository relative")
    lowered = str(normalized).lower()
    if any(token in lowered for token in _FORBIDDEN_LIVE_PATH_TOKENS):
        raise OracleIsolationError("ARC3 live adapter cannot load an oracle/debug artifact")
    required_prefix = ("demos", "human_play", "segmented")
    if normalized.parts[: len(required_prefix)] != required_prefix or normalized.suffix != ".jsonl":
        raise OracleIsolationError("ARC3 live adapter accepts only segmented public action trajectories")
    return normalized


def reject_offline_oracle_reference(reference: str) -> None:
    """Use at adapter boundaries before accepting a caller-provided artifact path."""

    lowered = reference.lower()
    if any(token in lowered for token in _FORBIDDEN_LIVE_PATH_TOKENS):
        raise OracleIsolationError("offline oracle/debug references are not live learner inputs")
