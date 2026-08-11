"""Auditable learning traces and native corpus-callosum SVG rendering."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence

from .model import ActionKind, Grid, grid_to_lists


@dataclass(frozen=True)
class TraceEvent:
    step: int
    action: ActionKind
    payload: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"step": self.step, "action": self.action.value, "payload": dict(self.payload)}


@dataclass
class LearningTrace:
    """Only explicit, externally reportable actions and evidence are retained."""

    episode_id: str
    events: list[TraceEvent] = field(default_factory=list)

    def record(self, action: ActionKind, **payload: Any) -> None:
        self.events.append(TraceEvent(len(self.events), action, payload))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "episode_id": self.episode_id,
            "reasoning_visibility": "explicit observable hypothesis/evidence/revision records only",
            "events": [event.as_dict() for event in self.events],
        }

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


_PALETTE = {
    0: "#111827",
    1: "#2563eb",
    2: "#dc2626",
    3: "#16a34a",
    4: "#facc15",
    5: "#6b21a8",
    6: "#111111",
    7: "#fb923c",
    8: "#22d3ee",
    9: "#7c2d12",
}


def _operator_label(selected_hypothesis: str) -> str:
    operator = selected_hypothesis.split("(", 1)[0]
    if operator == "fallback_identity_complete_grid":
        return "identity fallback"
    return operator if len(operator) <= 26 else f"{operator[:23]}..."


def _grid_svg(grid: Grid, left: int, top: int, maximum_size: int = 260) -> str:
    height = len(grid)
    width = len(grid[0])
    cell = max(8, min(28, maximum_size // max(height, width)))
    pieces = [
        f'<rect x="{left - 4}" y="{top - 4}" width="{width * cell + 8}" '
        f'height="{height * cell + 8}" rx="8" fill="#f8fafc" stroke="#475569"/>'
    ]
    for row_index, row in enumerate(grid):
        for column_index, color in enumerate(row):
            pieces.append(
                f'<rect x="{left + column_index * cell}" y="{top + row_index * cell}" '
                f'width="{cell - 1}" height="{cell - 1}" fill="{_PALETTE.get(color, "#94a3b8")}"/>'
            )
    return "".join(pieces)


def render_corpus_callosum_svg(
    path: Path,
    test_input: Grid,
    prediction: Grid,
    selected_hypothesis: str,
    trace: Mapping[str, Any],
) -> None:
    """Render a source-to-compatibility-to-output trace without invented causality."""

    events = trace.get("events", [])
    action_labels = [
        str(event.get("action"))
        for event in events
        if isinstance(event, Mapping) and isinstance(event.get("action"), str)
    ]
    action_text = (
        "ATTEND → PROPOSE → APPLY/COMPARE → COUNTEREXAMPLE → REVISE → COMMIT"
        if action_labels
        else "No recorded actions"
    )
    selected_operator = escape(_operator_label(selected_hypothesis))
    svg = "".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="620" viewBox="0 0 1280 620">',
            '<rect width="1280" height="620" fill="#f8fafc"/>',
            '<text x="48" y="55" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#0f172a">ARC123 Corpus-Callosum Trace</text>',
            '<text x="48" y="84" font-family="Arial, sans-serif" font-size="16" fill="#334155">Explicit evidence → compatibility support → complete candidate output</text>',
            '<text x="120" y="142" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#0f172a">Test input</text>',
            _grid_svg(test_input, 70, 165),
            '<path d="M 360 300 C 470 170, 510 170, 580 280" fill="none" stroke="#2563eb" stroke-width="12" stroke-linecap="round"/>',
            '<path d="M 360 330 C 470 450, 510 450, 580 340" fill="none" stroke="#7c3aed" stroke-width="12" stroke-linecap="round"/>',
            '<rect x="540" y="205" width="235" height="220" rx="24" fill="#ffffff" stroke="#334155" stroke-width="3"/>',
            '<text x="567" y="248" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#0f172a">Compatibility core</text>',
            '<text x="567" y="285" font-family="Arial, sans-serif" font-size="16" fill="#334155">UNKNOWN ≠ IMPOSSIBLE</text>',
            '<text x="567" y="319" font-family="Arial, sans-serif" font-size="15" fill="#334155">Exact contradictions: zero support</text>',
            '<text x="567" y="352" font-family="Arial, sans-serif" font-size="13" fill="#475569">Selected generic operator</text>',
            f'<text x="567" y="376" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#0f172a">{selected_operator}</text>',
            '<text x="567" y="405" font-family="Arial, sans-serif" font-size="13" fill="#475569">partial theories retained until refuted</text>',
            '<path d="M 775 280 C 870 170, 905 170, 1010 300" fill="none" stroke="#16a34a" stroke-width="12" stroke-linecap="round"/>',
            '<path d="M 775 340 C 870 450, 905 450, 1010 330" fill="none" stroke="#ea580c" stroke-width="12" stroke-linecap="round"/>',
            '<text x="1050" y="142" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#0f172a">Committed output</text>',
            _grid_svg(prediction, 990, 165),
            '<rect x="48" y="520" width="1184" height="55" rx="12" fill="#e2e8f0"/>',
            f'<text x="70" y="554" font-family="Arial, sans-serif" font-size="15" fill="#0f172a">Observable controller path: {escape(action_text)}</text>',
            '</svg>',
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def render_trace_markdown(trace: Mapping[str, Any]) -> str:
    """Render a concise public walkthrough without private chain-of-thought."""

    events = [event for event in trace.get("events", []) if isinstance(event, Mapping)]
    action_counts: dict[str, int] = {}
    for event in events:
        action = str(event.get("action"))
        action_counts[action] = action_counts.get(action, 0) + 1
    lines = [
        "## Observable IHL Walkthrough",
        "",
        "The record contains explicit actions, predictions, feedback, and revisions; it does not claim or store hidden model reasoning.",
        "",
        "### Action totals",
        "",
        *[f"- `{action}`: {count}" for action, count in sorted(action_counts.items())],
        "",
        "### Decision milestones",
        "",
    ]
    milestone_actions = {
        ActionKind.ATTEND.value,
        ActionKind.PROPOSE.value,
        ActionKind.SPECIALIZE.value,
        ActionKind.GENERALIZE.value,
        ActionKind.COMPOSE.value,
        ActionKind.MERGE_RULES.value,
        ActionKind.PROMOTE_CONSTRAINT.value,
        ActionKind.COMMIT.value,
    }
    for event in events:
        if event.get("action") not in milestone_actions:
            continue
        payload = event.get("payload", {})
        summary = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        lines.append(f"- `{event.get('step')}` `{event.get('action')}` — `{summary}`")
    counterexamples = [
        event
        for event in events
        if event.get("action") == ActionKind.FIND_COUNTEREXAMPLE.value
    ]
    if counterexamples:
        lines.extend(["", "### First counterexamples", ""])
        for event in counterexamples[:5]:
            payload = event.get("payload", {})
            lines.append(
                f"- `{event.get('step')}` — `{json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}`"
            )
        if len(counterexamples) > 5:
            lines.append(
                f"- `{len(counterexamples) - 5}` additional explicit counterexamples are retained in `learning_trace.json`."
            )
    return "\n".join(lines) + "\n"
