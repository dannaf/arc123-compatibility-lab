"""Source-pinned ARC3 observable-transition adapter with oracle-path isolation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from ..contracts import EvidenceObservation, EnvironmentAction, TransitionFeedback
from ..isolation import OracleIsolationError, require_public_arc3_transition_path


@dataclass(frozen=True)
class ExternalTransition:
    """Compatibility shim for callers that use the earlier ARC3 adapter surface."""

    observation: Mapping[str, Any]
    progress: float | None
    terminal: bool


class ARC3Environment(Protocol):
    """External-action adapter contract shared with the benchmark-neutral core."""

    def observe(self) -> EvidenceObservation: ...

    def available_actions(self) -> Sequence[EnvironmentAction]: ...

    def act(self, action: EnvironmentAction) -> TransitionFeedback: ...


def _git_output(repository_root: Path, arguments: Sequence[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository_root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise OracleIsolationError("cannot read the pinned public ARC3 transition source") from error
    return result.stdout


def _validated_records(raw_jsonl: str) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(raw_jsonl.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise OracleIsolationError(
                f"ARC3 transition record {line_number} is not valid JSON"
            ) from error
        if not isinstance(record, Mapping):
            raise OracleIsolationError("ARC3 transition records must be JSON objects")
        if not isinstance(record.get("frame"), list) or not isinstance(record.get("action"), str):
            raise OracleIsolationError("ARC3 transition record lacks observable frame/action data")
        available = record.get("available")
        if not isinstance(available, list) or not all(isinstance(item, str) for item in available):
            raise OracleIsolationError("ARC3 transition record lacks observable available actions")
        records.append(dict(record))
    if len(records) < 3:
        raise OracleIsolationError("ARC3 transition replay requires an initial state and two probes")
    return tuple(records)


@dataclass
class SourcePinnedARC3ReplayWorld:
    """A non-simulated replay over recorded public game transitions.

    The adapter keeps the source location and hash private to its reporting method.
    Its controller-facing observation exposes one current public state and its available
    actions only. An unrecorded action is refused rather than being simulated.
    """

    _world_id: str
    _records: tuple[Mapping[str, Any], ...]
    _source_repository: str
    _source_commit: str
    _source_path: str
    _source_sha256: str
    _cursor: int = 0

    @classmethod
    def from_git_source(
        cls,
        source_root: Path,
        source_commit: str,
        source_path: str,
        *,
        world_id: str = "arc3-public-replay",
        source_repository: str = "https://github.com/dannaf/SingularityML",
    ) -> "SourcePinnedARC3ReplayWorld":
        normalized_path = require_public_arc3_transition_path(source_path)
        resolved_commit = _git_output(source_root, ["rev-parse", f"{source_commit}^{{commit}}"]).strip()
        if resolved_commit != source_commit:
            raise OracleIsolationError("ARC3 source commit does not resolve to the requested pin")
        raw_jsonl = _git_output(source_root, ["show", f"{source_commit}:{normalized_path}"])
        records = _validated_records(raw_jsonl)
        return cls(
            _world_id=world_id,
            _records=records,
            _source_repository=source_repository,
            _source_commit=source_commit,
            _source_path=str(normalized_path),
            _source_sha256=hashlib.sha256(raw_jsonl.encode("utf-8")).hexdigest(),
        )

    @property
    def transition_count(self) -> int:
        return len(self._records) - 1

    def _observation_for(self, cursor: int) -> EvidenceObservation:
        record = self._records[cursor]
        return EvidenceObservation(
            observation_id=f"{self._world_id}:step:{record.get('step', cursor)}",
            world_id=self._world_id,
            observation_kind="external_public_game_state",
            payload={
                "frame": record["frame"],
                "available_actions": list(record["available"]),
                "score": record.get("score"),
                "levels_completed": record.get("levels_completed"),
                "state": record.get("state"),
            },
            metadata={
                "oracle_visible": False,
                "source_category": "observable_real_action_trajectory",
                "replay_cursor": cursor,
            },
        )

    def observe(self) -> EvidenceObservation:
        return self._observation_for(self._cursor)

    def agent_view(self) -> dict[str, Any]:
        """Return only the current observable state; source pin and future records stay hidden."""

        return self.observe().as_dict()

    def available_actions(self) -> tuple[EnvironmentAction, ...]:
        record = self._records[self._cursor]
        return tuple(EnvironmentAction("external_key", {"key": key}) for key in record["available"])

    def act(self, action: EnvironmentAction) -> TransitionFeedback:
        before = self.observe()
        requested_key = action.parameters.get("key")
        available = {item.parameters["key"] for item in self.available_actions()}
        if action.action_type != "external_key" or not isinstance(requested_key, str):
            return TransitionFeedback(
                action=action,
                before=before,
                after=before,
                accepted=False,
                changed=None,
                progress=None,
                terminal=False,
                metadata={"reason": "external ARC3 actions require a current public key"},
            )
        if requested_key not in available:
            return TransitionFeedback(
                action=action,
                before=before,
                after=before,
                accepted=False,
                changed=None,
                progress=None,
                terminal=False,
                metadata={"reason": "key is not available in the observed public state"},
            )
        if self._cursor + 1 >= len(self._records):
            return TransitionFeedback(
                action=action,
                before=before,
                after=before,
                accepted=False,
                changed=None,
                progress=None,
                terminal=True,
                metadata={"reason": "no further recorded public transition"},
            )
        next_record = self._records[self._cursor + 1]
        if requested_key != next_record["action"]:
            return TransitionFeedback(
                action=action,
                before=before,
                after=before,
                accepted=False,
                changed=None,
                progress=None,
                terminal=False,
                metadata={
                    "reason": "selected key has no matching observed replay transition; no state was simulated"
                },
            )
        self._cursor += 1
        after = self.observe()
        progress_value = next_record.get("levels_completed")
        progress = float(progress_value) if isinstance(progress_value, (int, float)) else None
        state = str(next_record.get("state", ""))
        terminal = state.endswith("FINISHED") and not state.endswith("NOT_FINISHED")
        return TransitionFeedback(
            action=action,
            before=before,
            after=after,
            accepted=True,
            changed=(bool(next_record["changed"]) if "changed" in next_record else None),
            progress=progress,
            terminal=terminal,
            metadata={"transition_source": "recorded_public_action_outcome"},
        )

    def offline_provenance_for_report(self) -> dict[str, str]:
        """Expose the source pin only to an offline report/V&V caller after the run."""

        return {
            "repository": self._source_repository,
            "commit": self._source_commit,
            "path": self._source_path,
            "sha256": self._source_sha256,
            "url": f"{self._source_repository}/blob/{self._source_commit}/{self._source_path}",
        }
