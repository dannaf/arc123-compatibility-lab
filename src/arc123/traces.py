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
    if selected_hypothesis == "fallback_identity_complete_grid":
        return "identity fallback"
    if "dihedral_tile" in selected_hypothesis:
        return "dihedral macro-tile"
    operator = selected_hypothesis.split("(", 1)[0]
    return operator if len(operator) <= 26 else f"{operator[:23]}..."


def _grid_svg(
    grid: Grid,
    left: int,
    top: int,
    maximum_size: int = 260,
    minimum_cell: int = 8,
    highlighted_cells: Sequence[tuple[int, int]] = (),
) -> str:
    height = len(grid)
    width = len(grid[0])
    cell = max(minimum_cell, min(28, maximum_size // max(height, width)))
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
    for row_index, column_index in highlighted_cells:
        pieces.append(
            f'<rect x="{left + column_index * cell - 1}" y="{top + row_index * cell - 1}" '
            f'width="{cell + 1}" height="{cell + 1}" fill="none" stroke="#e11d48" stroke-width="2"/>'
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
    if "dihedral_tile" in selected_hypothesis:
        action_text = "ATTEND → PROPOSE → APPLY/COMPARE → UNKNOWN RESIDUAL → REVISE/COMPOSE → COMMIT"
    elif not action_labels:
        action_text = "No recorded actions"
    elif (
        ActionKind.EXPLAIN_RESIDUAL.value in action_labels
        and ActionKind.FIND_COUNTEREXAMPLE.value not in action_labels
    ):
        action_text = "ATTEND → PROPOSE → APPLY/COMPARE → UNKNOWN RESIDUAL → REVISE/COMPOSE → COMMIT"
    else:
        action_text = "ATTEND → PROPOSE → APPLY/COMPARE → COUNTEREXAMPLE → REVISE → COMMIT"
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


def render_arc3_transition_svg(
    path: Path,
    before: Grid,
    after: Grid,
    trace: Mapping[str, Any],
) -> None:
    """Render only observed public ARC3 states and explicit probe/revision events."""

    events = [event for event in trace.get("events", []) if isinstance(event, Mapping)]
    probe_events = [
        event for event in events if event.get("action") == ActionKind.APPLY_LOCALLY.value
    ]
    first_probe = probe_events[0].get("payload", {}) if probe_events else {}
    transition = first_probe.get("transition", {}) if isinstance(first_probe, Mapping) else {}
    action = transition.get("action", {}) if isinstance(transition, Mapping) else {}
    parameters = action.get("parameters", {}) if isinstance(action, Mapping) else {}
    key = escape(str(parameters.get("key", "unknown action")))
    confirmed = any(
        event.get("action") == ActionKind.PROMOTE_CONSTRAINT.value for event in events
    )
    verdict = "confirmed on two observed transitions" if confirmed else "not confirmed"
    changed_cells = [
        (row, column)
        for row, (before_row, after_row) in enumerate(zip(before, after))
        for column, (before_cell, after_cell) in enumerate(zip(before_row, after_row))
        if before_cell != after_cell
    ]
    svg = "".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1420" height="680" viewBox="0 0 1420 680">',
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#2563eb"/></marker></defs>',
            '<rect width="1420" height="680" fill="#f8fafc"/>',
            '<text x="44" y="52" font-family="Arial, sans-serif" font-size="29" font-weight="700" fill="#0f172a">ARC123 Real-Transition Corpus-Callosum Trace</text>',
            '<text x="44" y="81" font-family="Arial, sans-serif" font-size="16" fill="#334155">Recorded public state -> deliberate external probe -> observed refutation -> revised effect hypothesis -> exploit</text>',
            '<text x="90" y="138" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#0f172a">Observed state before probe</text>',
            _grid_svg(
                before,
                76,
                160,
                maximum_size=230,
                minimum_cell=2,
                highlighted_cells=changed_cells,
            ),
            '<line x1="330" y1="302" x2="528" y2="302" stroke="#2563eb" stroke-width="9" stroke-linecap="round" marker-end="url(#arrow)"/>',
            '<line x1="330" y1="350" x2="528" y2="350" stroke="#7c3aed" stroke-width="9" stroke-linecap="round" marker-end="url(#arrow)"/>',
            '<rect x="538" y="198" width="335" height="254" rx="24" fill="#ffffff" stroke="#334155" stroke-width="3"/>',
            '<text x="568" y="239" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#0f172a">Shared compatibility core</text>',
            '<text x="568" y="279" font-family="Arial, sans-serif" font-size="16" fill="#334155">H1: selected action is static</text>',
            f'<text x="568" y="313" font-family="Arial, sans-serif" font-size="16" fill="#334155">Probe: {key}</text>',
            '<text x="568" y="347" font-family="Arial, sans-serif" font-size="16" fill="#334155">Observed change refutes H1</text>',
            '<text x="568" y="381" font-family="Arial, sans-serif" font-size="16" fill="#334155">H2: state change is possible</text>',
            f'<text x="568" y="415" font-family="Arial, sans-serif" font-size="15" fill="#475569">{escape(verdict)}</text>',
            '<line x1="883" y1="302" x2="1070" y2="302" stroke="#16a34a" stroke-width="9" stroke-linecap="round" marker-end="url(#arrow)"/>',
            '<line x1="883" y1="350" x2="1070" y2="350" stroke="#ea580c" stroke-width="9" stroke-linecap="round" marker-end="url(#arrow)"/>',
            '<text x="1090" y="138" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#0f172a">Observed state after probe</text>',
            _grid_svg(
                after,
                1088,
                160,
                maximum_size=230,
                minimum_cell=2,
                highlighted_cells=changed_cells,
            ),
            '<rect x="44" y="560" width="1332" height="70" rx="12" fill="#e2e8f0"/>',
            '<text x="66" y="591" font-family="Arial, sans-serif" font-size="15" fill="#0f172a">Red outlines mark cells changed by the recorded probe. All displayed cells are source-pinned public frames; no oracle rule, future trajectory, or simulation is exposed.</text>',
            '<text x="66" y="615" font-family="Arial, sans-serif" font-size="15" fill="#0f172a">This validates a shared observation/action/revision contract, not an ARC3 level-solve claim.</text>',
            '</svg>',
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def _compact_trace_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        compact: dict[str, Any] = {}
        for key, child in value.items():
            if key == "frame" and isinstance(child, list) and child and all(
                isinstance(row, list) and row for row in child
            ):
                colors = sorted(
                    {cell for row in child for cell in row if isinstance(cell, int)}
                )
                compact[key] = {
                    "grid_summary": {
                        "height": len(child),
                        "width": len(child[0]),
                        "colors": colors,
                    }
                }
            else:
                compact[str(key)] = _compact_trace_value(child)
        return compact
    if isinstance(value, list):
        return [_compact_trace_value(item) for item in value]
    if isinstance(value, tuple):
        return [_compact_trace_value(item) for item in value]
    return value


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
        summary = json.dumps(
            _compact_trace_value(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
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
                f"- `{event.get('step')}` — `{json.dumps(_compact_trace_value(payload), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}`"
            )
        if len(counterexamples) > 5:
            lines.append(
                f"- `{len(counterexamples) - 5}` additional explicit counterexamples are retained in `learning_trace.json`."
            )
    return "\n".join(lines) + "\n"
