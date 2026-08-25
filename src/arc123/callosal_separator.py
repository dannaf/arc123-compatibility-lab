"""Generic finite semantic-separator learning for Forward–Backward Singularity Learning.

The learner receives observations with a typed descriptor dictionary and an
observed effect. It exhaustively searches descriptor subsets and chooses a
minimum-description deterministic separator: first minimum arity, then the
smallest induced semantic table (maximum reuse/compression), then deterministic
lexical tie-breaking.

This is intentionally domain-independent: rows, objects, frames, transitions,
and ARC3 state/action records can all feed the same core once perception has
produced descriptors. It is complete relative to the supplied finite
descriptor vocabulary and configured maximum separator arity.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Hashable, Iterable, Mapping, Optional, Sequence

SemanticValue = Hashable


@dataclass(frozen=True)
class SemanticObservation:
    """One local evidence record crossing a candidate corpus-callosum interface."""

    descriptors: Mapping[str, SemanticValue]
    effect: SemanticValue


@dataclass(frozen=True)
class SeparatorModel:
    """Minimal deterministic forward separator with explicit reverse fibers."""

    descriptor_names: tuple[str, ...]
    forward_table: tuple[tuple[tuple[SemanticValue, ...], SemanticValue], ...]

    @property
    def arity(self) -> int:
        return len(self.descriptor_names)

    @property
    def mapping(self) -> dict[tuple[SemanticValue, ...], SemanticValue]:
        return dict(self.forward_table)

    @property
    def reverse_fibers(self) -> dict[SemanticValue, tuple[tuple[SemanticValue, ...], ...]]:
        fibers: dict[SemanticValue, list[tuple[SemanticValue, ...]]] = {}
        for key, effect in self.forward_table:
            fibers.setdefault(effect, []).append(key)
        return {
            effect: tuple(sorted(keys, key=repr))
            for effect, keys in fibers.items()
        }

    @property
    def backward_deterministic(self) -> bool:
        return all(len(keys) == 1 for keys in self.reverse_fibers.values())

    def key_for(self, descriptors: Mapping[str, SemanticValue]) -> Optional[tuple[SemanticValue, ...]]:
        try:
            return tuple(descriptors[name] for name in self.descriptor_names)
        except KeyError:
            return None

    def predict(self, descriptors: Mapping[str, SemanticValue]) -> Optional[SemanticValue]:
        """Return the effect, or UNKNOWN (`None`) for an unsupported semantic key."""

        key = self.key_for(descriptors)
        if key is None:
            return None
        return self.mapping.get(key)

    def causes_for(self, effect: SemanticValue) -> tuple[tuple[SemanticValue, ...], ...]:
        """Backward/abductive view: all observed separator keys supporting an effect."""

        return self.reverse_fibers.get(effect, ())

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "descriptor_names": self.descriptor_names,
            "separator_arity": self.arity,
            "forward_rows": len(self.forward_table),
            "forward_deterministic": True,
            "backward_deterministic": self.backward_deterministic,
            "reverse_fiber_sizes": {
                repr(effect): len(keys) for effect, keys in self.reverse_fibers.items()
            },
        }


def _deterministic_table(
    observations: Sequence[SemanticObservation], descriptor_names: tuple[str, ...]
) -> Optional[dict[tuple[SemanticValue, ...], SemanticValue]]:
    table: dict[tuple[SemanticValue, ...], SemanticValue] = {}
    sentinel = object()
    for observation in observations:
        try:
            key = tuple(observation.descriptors[name] for name in descriptor_names)
        except KeyError:
            return None
        prior = table.get(key, sentinel)
        if prior is not sentinel and prior != observation.effect:
            return None
        table[key] = observation.effect
    return table


def _support_score(
    observations: Sequence[SemanticObservation], descriptor_names: tuple[str, ...]
) -> tuple[int, int]:
    """Return (reused observations, minimum key support) for deterministic tie-breaking."""

    counts: dict[tuple[SemanticValue, ...], int] = {}
    for observation in observations:
        key = tuple(observation.descriptors[name] for name in descriptor_names)
        counts[key] = counts.get(key, 0) + 1
    reused = sum(max(0, count - 1) for count in counts.values())
    minimum_support = min(counts.values()) if counts else 0
    return reused, minimum_support


def learn_minimal_separator(
    observations: Sequence[SemanticObservation],
    candidate_descriptors: Iterable[str] | None = None,
    *,
    max_arity: int | None = None,
    require_effect_variation: bool = True,
) -> Optional[SeparatorModel]:
    """Find a minimum-description deterministic descriptor subset.

    For each arity, all descriptor subsets are exhaustively checked. Among
    deterministic subsets of the *minimum arity*, the learner prefers:

    1. fewer distinct semantic keys / forward-table rows;
    2. greater repeated support for those keys;
    3. greater minimum per-key support;
    4. lexical descriptor order for reproducibility.

    Thus accidental unique identifiers (for example one frame color per
    demonstration) lose to a structural descriptor that reuses the same rule
    across demonstrations. For a finite descriptor set D and arity cap k, if
    any subset of D of size <= k deterministically realizes the observations,
    one of minimum arity is guaranteed to be returned.

    `require_effect_variation=True` prevents a vacuous constant explanation
    from being treated as a discovered semantic dependency.
    """

    if not observations:
        return None
    effects = {observation.effect for observation in observations}
    if require_effect_variation and len(effects) < 2:
        return None

    if candidate_descriptors is None:
        names = sorted(
            set.intersection(*(set(observation.descriptors) for observation in observations))
        )
    else:
        names = sorted(set(candidate_descriptors))
        if any(not set(names).issubset(observation.descriptors) for observation in observations):
            return None

    if not names:
        return None
    limit = len(names) if max_arity is None else min(max_arity, len(names))
    for arity in range(1, limit + 1):
        viable: list[
            tuple[
                int,
                int,
                int,
                tuple[str, ...],
                dict[tuple[SemanticValue, ...], SemanticValue],
            ]
        ] = []
        for subset in combinations(names, arity):
            table = _deterministic_table(observations, subset)
            if table is None:
                continue
            reused, minimum_support = _support_score(observations, subset)
            viable.append((len(table), -reused, -minimum_support, subset, table))
        if viable:
            _, _, _, subset, table = min(viable, key=lambda item: item[:4])
            rows = tuple(sorted(table.items(), key=lambda item: repr(item[0])))
            return SeparatorModel(subset, rows)
    return None


def separator_exists(
    observations: Sequence[SemanticObservation],
    candidate_descriptors: Iterable[str],
    max_arity: int,
) -> bool:
    """Decision form used by relative-completeness regression tests."""

    return (
        learn_minimal_separator(
            observations,
            candidate_descriptors,
            max_arity=max_arity,
            require_effect_variation=False,
        )
        is not None
    )
