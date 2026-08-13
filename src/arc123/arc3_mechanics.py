"""Generic public-history perceptions for bounded ARC3 mechanics experiments."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import inf
from typing import Any, Mapping, Sequence

from .contracts import EnvironmentAction, EvidenceObservation, TransitionFeedback
from .model import Grid, grid_from
from .perceptions import Component, connected_components


@dataclass(frozen=True)
class ComponentSignature:
    """A color and translation-invariant shape signature for an observed component."""

    color: int
    area: int
    shape: tuple[tuple[int, int], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "color": self.color,
            "area": self.area,
            "shape": [list(cell) for cell in self.shape],
        }


@dataclass(frozen=True)
class ComponentFeature:
    """An observable component instance with a reusable signature and center."""

    signature: ComponentSignature
    center: tuple[float, float]
    bbox: tuple[int, int, int, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "signature": self.signature.as_dict(),
            "center": [self.center[0], self.center[1]],
            "bbox": list(self.bbox),
        }


@dataclass(frozen=True)
class ActionEffect:
    """An action's observed modal translation for one controlled component."""

    key: str
    delta: tuple[float, float]
    support_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "delta": [self.delta[0], self.delta[1]],
            "support_count": self.support_count,
        }


@dataclass(frozen=True)
class MotionModel:
    """A bounded action-motion model induced only from observed past transitions."""

    controlled_component: ComponentSignature
    action_effects: tuple[ActionEffect, ...]
    co_moving_colors: tuple[int, ...]
    co_moving_components: tuple[ComponentSignature, ...]
    beacon_signatures: tuple[ComponentSignature, ...]
    history_transition_count: int

    def effect_for(self, action_key: str) -> ActionEffect | None:
        return next((effect for effect in self.action_effects if effect.key == action_key), None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "controlled_component": self.controlled_component.as_dict(),
            "action_effects": [effect.as_dict() for effect in self.action_effects],
            "co_moving_colors": list(self.co_moving_colors),
            "co_moving_components": [
                signature.as_dict() for signature in self.co_moving_components
            ],
            "beacon_signatures": [signature.as_dict() for signature in self.beacon_signatures],
            "history_transition_count": self.history_transition_count,
            "unobserved_actions_remain_unknown": True,
        }


@dataclass(frozen=True)
class GoalDirectedAction:
    """An auditable action choice against a visible, current geometric relation."""

    action: EnvironmentAction
    default_action: EnvironmentAction | None
    primary_component: ComponentFeature
    goal_relation_component: ComponentFeature
    beacon: ComponentFeature
    predicted_delta: tuple[float, float]
    goal_distance_before: float
    goal_distance_after: float
    aligned_axis: str
    aligned_axis_residual_after: float

    @property
    def is_non_default(self) -> bool:
        if self.default_action is None:
            return False
        return self.action != self.default_action

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.as_dict(),
            "default_action": (
                self.default_action.as_dict() if self.default_action is not None else None
            ),
            "is_non_default": self.is_non_default,
            "primary_component": self.primary_component.as_dict(),
            "goal_relation_component": self.goal_relation_component.as_dict(),
            "beacon": self.beacon.as_dict(),
            "predicted_delta": [self.predicted_delta[0], self.predicted_delta[1]],
            "goal_distance_before": self.goal_distance_before,
            "goal_distance_after": self.goal_distance_after,
            "aligned_axis": self.aligned_axis,
            "aligned_axis_residual_after": self.aligned_axis_residual_after,
            "selection_rule": "visible_axis_alignment_then_goal_distance",
        }


def _grid_from_observation(observation: EvidenceObservation) -> Grid:
    raw_frame = observation.payload.get("frame")
    if not isinstance(raw_frame, Sequence):
        raise ValueError("public ARC3 observation lacks a grid frame")
    return grid_from(raw_frame, "public ARC3 frame")


def _signature(component: Component) -> ComponentSignature:
    top, left, _, _ = component.bbox
    return ComponentSignature(
        color=component.color,
        area=component.area,
        shape=tuple((row - top, column - left) for row, column in component.cells),
    )


def _feature(component: Component) -> ComponentFeature:
    row_center = sum(row for row, _ in component.cells) / component.area
    column_center = sum(column for _, column in component.cells) / component.area
    return ComponentFeature(_signature(component), (row_center, column_center), component.bbox)


def _features(grid: Grid) -> tuple[ComponentFeature, ...]:
    return tuple(_feature(component) for component in connected_components(grid, connectivity=8))


def _features_by_signature(
    features: Sequence[ComponentFeature],
) -> dict[ComponentSignature, tuple[ComponentFeature, ...]]:
    grouped: dict[ComponentSignature, list[ComponentFeature]] = defaultdict(list)
    for feature in features:
        grouped[feature.signature].append(feature)
    return {signature: tuple(items) for signature, items in grouped.items()}


def _action_key(feedback: TransitionFeedback) -> str | None:
    raw_key = feedback.action.parameters.get("key")
    return raw_key if isinstance(raw_key, str) and raw_key else None


def _center_delta(before: ComponentFeature, after: ComponentFeature) -> tuple[float, float]:
    return (
        round(after.center[0] - before.center[0], 6),
        round(after.center[1] - before.center[1], 6),
    )


def _squared_distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return (first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2


def _mode_effect(deltas: Sequence[tuple[float, float]]) -> tuple[tuple[float, float], int]:
    counts = Counter(deltas)
    delta, support_count = min(counts.items(), key=lambda item: (-item[1], item[0]))
    return delta, support_count


def _history_frames(history: Sequence[TransitionFeedback]) -> tuple[Grid, ...]:
    frames: list[Grid] = []
    for feedback in history:
        before = _grid_from_observation(feedback.before)
        after = _grid_from_observation(feedback.after)
        if not frames or frames[-1] != before:
            frames.append(before)
        if frames[-1] != after:
            frames.append(after)
    return tuple(frames)


def learn_motion_model(history: Sequence[TransitionFeedback]) -> MotionModel:
    """Infer action translations and stable related beacons from public history only."""

    if len(history) < 2:
        raise ValueError("motion learning requires at least two public transitions")
    delta_observations: dict[
        ComponentSignature, dict[str, list[tuple[float, float]]]
    ] = defaultdict(lambda: defaultdict(list))
    for feedback in history:
        action_key = _action_key(feedback)
        if not feedback.accepted or action_key is None:
            continue
        before_features = _features_by_signature(_features(_grid_from_observation(feedback.before)))
        after_features = _features_by_signature(_features(_grid_from_observation(feedback.after)))
        for signature, before_items in before_features.items():
            after_items = after_features.get(signature, ())
            if len(before_items) != 1 or len(after_items) != 1:
                continue
            delta = _center_delta(before_items[0], after_items[0])
            if delta != (0.0, 0.0):
                delta_observations[signature][action_key].append(delta)
    candidate_effects: list[tuple[ComponentSignature, tuple[ActionEffect, ...]]] = []
    for signature, per_action in delta_observations.items():
        effects = tuple(
            ActionEffect(action_key, *_mode_effect(deltas))
            for action_key, deltas in sorted(per_action.items())
            if deltas
        )
        if len(effects) >= 2:
            candidate_effects.append((signature, effects))
    if not candidate_effects:
        raise ValueError("public history contains no repeatable action-motion relation")
    controlled_signature, action_effects = min(
        candidate_effects,
        key=lambda item: (
            -len(item[1]),
            -sum(effect.support_count for effect in item[1]),
            item[0].area,
            item[0].color,
            item[0].shape,
        ),
    )
    controlled_effects = {effect.key: effect.delta for effect in action_effects}
    co_moving_colors = {controlled_signature.color}
    co_moving_components = {controlled_signature}
    for signature, effects in candidate_effects:
        effect_map = {effect.key: effect.delta for effect in effects}
        shared_actions = set(effect_map) & set(controlled_effects)
        if len(shared_actions) < 2:
            continue
        if all(effect_map[action_key] == controlled_effects[action_key] for action_key in shared_actions):
            co_moving_colors.add(signature.color)
            co_moving_components.add(signature)
    frames = _history_frames(history)
    centers_by_signature: dict[ComponentSignature, list[tuple[float, float]]] = defaultdict(list)
    presence_by_signature: Counter[ComponentSignature] = Counter()
    for frame in frames:
        frame_features = _features_by_signature(_features(frame))
        for signature, items in frame_features.items():
            if len(items) == 1:
                centers_by_signature[signature].append(items[0].center)
                presence_by_signature[signature] += 1
    stable_beacons = tuple(
        sorted(
            (
                signature
                for signature, centers in centers_by_signature.items()
                if presence_by_signature[signature] == len(frames)
                and len(set(centers)) == 1
                and signature.color in co_moving_colors
                and signature != controlled_signature
                and signature.area <= controlled_signature.area
            ),
            key=lambda signature: (signature.area, signature.color, signature.shape),
        )
    )
    if not stable_beacons:
        raise ValueError("public history contains no stable related beacon")
    return MotionModel(
        controlled_component=controlled_signature,
        action_effects=action_effects,
        co_moving_colors=tuple(sorted(co_moving_colors)),
        co_moving_components=tuple(
            sorted(
                co_moving_components,
                key=lambda signature: (signature.area, signature.color, signature.shape),
            )
        ),
        beacon_signatures=stable_beacons,
        history_transition_count=len(history),
    )


def choose_goal_directed_action(
    model: MotionModel,
    observation: EvidenceObservation,
    available_actions: Sequence[EnvironmentAction],
) -> GoalDirectedAction | None:
    """Choose a current public action that reduces an observed beacon relation."""

    current_features = _features_by_signature(_features(_grid_from_observation(observation)))
    controlled_items = current_features.get(model.controlled_component, ())
    if len(controlled_items) != 1:
        return None
    controlled = controlled_items[0]
    moving_items = [
        item
        for signature in model.co_moving_components
        for item in current_features.get(signature, ())
    ]
    if not moving_items:
        return None
    beacon_options = [
        item
        for signature in model.beacon_signatures
        for item in current_features.get(signature, ())
        if any(_squared_distance(moving.center, item.center) > 0.0 for moving in moving_items)
    ]
    if not beacon_options:
        return None
    beacon = min(
        beacon_options,
        key=lambda item: (
            min(_squared_distance(moving.center, item.center) for moving in moving_items),
            item.signature.area,
            item.signature.color,
            item.center,
        ),
    )
    default_action = min(
        available_actions,
        key=lambda action: (action.action_type, str(action.parameters.get("key", ""))),
        default=None,
    )
    goal_distance_before = min(
        _squared_distance(moving.center, beacon.center) for moving in moving_items
    )
    best_choice: GoalDirectedAction | None = None
    best_key: tuple[float, float, str] = (inf, inf, "")
    for action in available_actions:
        raw_key = action.parameters.get("key")
        if not isinstance(raw_key, str):
            continue
        effect = model.effect_for(raw_key)
        if effect is None:
            continue
        predicted_components = [
            (
                moving,
                (moving.center[0] + effect.delta[0], moving.center[1] + effect.delta[1]),
            )
            for moving in moving_items
        ]
        relation_component, predicted_center = min(
            predicted_components,
            key=lambda item: _squared_distance(item[1], beacon.center),
        )
        goal_distance_after = _squared_distance(predicted_center, beacon.center)
        if goal_distance_after >= goal_distance_before:
            continue
        if abs(effect.delta[0]) >= abs(effect.delta[1]):
            aligned_axis = "row"
            axis_residual = abs(beacon.center[0] - predicted_center[0])
        else:
            aligned_axis = "column"
            axis_residual = abs(beacon.center[1] - predicted_center[1])
        choice = GoalDirectedAction(
            action=action,
            default_action=default_action,
            primary_component=controlled,
            goal_relation_component=relation_component,
            beacon=beacon,
            predicted_delta=effect.delta,
            goal_distance_before=goal_distance_before,
            goal_distance_after=goal_distance_after,
            aligned_axis=aligned_axis,
            aligned_axis_residual_after=axis_residual,
        )
        choice_key = (axis_residual, goal_distance_after, raw_key)
        if choice_key < best_key:
            best_choice = choice
            best_key = choice_key
    return best_choice


def observed_controlled_delta(
    model: MotionModel,
    before: EvidenceObservation,
    after: EvidenceObservation,
) -> tuple[float, float] | None:
    """Read the controlled-component displacement from an observed feedback pair."""

    before_items = _features_by_signature(_features(_grid_from_observation(before))).get(
        model.controlled_component, ()
    )
    after_items = _features_by_signature(_features(_grid_from_observation(after))).get(
        model.controlled_component, ()
    )
    if len(before_items) != 1 or len(after_items) != 1:
        return None
    return _center_delta(before_items[0], after_items[0])
