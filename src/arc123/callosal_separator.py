"""Generic finite semantic-separator learning for Forward–Backward Singularity Learning.

The learner receives observations with a typed descriptor dictionary and an
observed effect. It exhaustively searches descriptor subsets.  Crucially, it
can return the *fiber* of all equally minimum-description deterministic
separators rather than silently choosing one lexical representative.  That is
necessary when the demonstrations do not identify one semantic coordinate:
ambiguity is retained until downstream prediction singularity, not erased by
a tie-break.

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
    counts: dict[tuple[SemanticValue, ...], int] = {}
    for observation in observations:
        key = tuple(observation.descriptors[name] for name in descriptor_names)
        counts[key] = counts.get(key, 0) + 1
    reused = sum(max(0, count - 1) for count in counts.values())
    minimum_support = min(counts.values()) if counts else 0
    return reused, minimum_support


def _value_encoding_cost(value: SemanticValue) -> int:
    """A small type-aware MDL proxy for semantic-domain complexity."""

    if isinstance(value, bool):
        return 1
    if isinstance(value, int):
        return 3 + abs(value).bit_length()
    if isinstance(value, str):
        return 2 + len(value)
    if isinstance(value, tuple):
        return 2 + sum(_value_encoding_cost(item) for item in value)
    if value is None:
        return 1
    return 4 + len(repr(value))


def _domain_encoding_cost(
    observations: Sequence[SemanticObservation], descriptor_names: tuple[str, ...]
) -> int:
    cost = 0
    for name in descriptor_names:
        values = {observation.descriptors[name] for observation in observations}
        cost += sum(_value_encoding_cost(value) for value in values)
    return cost


def _score_subset(
    observations: Sequence[SemanticObservation],
    subset: tuple[str, ...],
    table: Mapping[tuple[SemanticValue, ...], SemanticValue],
) -> tuple[int, int, int, int]:
    reused, minimum_support = _support_score(observations, subset)
    return (
        len(table),
        -reused,
        -minimum_support,
        _domain_encoding_cost(observations, subset),
    )


def learn_minimal_separator_fiber(
    observations: Sequence[SemanticObservation],
    candidate_descriptors: Iterable[str] | None = None,
    *,
    max_arity: int | None = None,
    require_effect_variation: bool = True,
) -> tuple[SeparatorModel, ...]:
    """Return every equally minimum-description exact separator.

    Search is exhaustive by arity. At the first arity having any deterministic
    representation, all subsets are scored by table compression, repeated
    support, minimum support and semantic-domain encoding. Every subset tied at
    the optimal score is retained.  Lexical order makes the returned tuple
    reproducible but does *not* erase the tie.

    This is the correct object for singularity learning: if several semantic
    explanations remain observationally indistinguishable, downstream code can
    ask whether they nevertheless induce one prediction.  It must not invent a
    unique latent program merely because one descriptor name sorts first.
    """

    if not observations:
        return ()
    effects = {observation.effect for observation in observations}
    if require_effect_variation and len(effects) < 2:
        return ()

    if candidate_descriptors is None:
        names = sorted(
            set.intersection(*(set(observation.descriptors) for observation in observations))
        )
    else:
        names = sorted(set(candidate_descriptors))
        if any(not set(names).issubset(observation.descriptors) for observation in observations):
            return ()

    if not names:
        return ()
    limit = len(names) if max_arity is None else min(max_arity, len(names))
    for arity in range(1, limit + 1):
        viable: list[
            tuple[
                tuple[int, int, int, int],
                tuple[str, ...],
                dict[tuple[SemanticValue, ...], SemanticValue],
            ]
        ] = []
        for subset in combinations(names, arity):
            table = _deterministic_table(observations, subset)
            if table is None:
                continue
            viable.append((_score_subset(observations, subset, table), subset, table))
        if viable:
            best_score = min(item[0] for item in viable)
            tied = [item for item in viable if item[0] == best_score]
            models = []
            for _, subset, table in sorted(tied, key=lambda item: item[1]):
                rows = tuple(sorted(table.items(), key=lambda item: repr(item[0])))
                models.append(SeparatorModel(subset, rows))
            return tuple(models)
    return ()


def learn_minimal_separator(
    observations: Sequence[SemanticObservation],
    candidate_descriptors: Iterable[str] | None = None,
    *,
    max_arity: int | None = None,
    require_effect_variation: bool = True,
) -> Optional[SeparatorModel]:
    """Compatibility wrapper returning one reproducible member of the optimum fiber.

    New code that can preserve semantic ambiguity should call
    :func:`learn_minimal_separator_fiber`.  This wrapper exists for simple
    consumers whose downstream behavior is invariant across an optimum tie.
    """

    fiber = learn_minimal_separator_fiber(
        observations,
        candidate_descriptors,
        max_arity=max_arity,
        require_effect_variation=require_effect_variation,
    )
    return fiber[0] if fiber else None


def separator_exists(
    observations: Sequence[SemanticObservation],
    candidate_descriptors: Iterable[str],
    max_arity: int,
) -> bool:
    return bool(
        learn_minimal_separator_fiber(
            observations,
            candidate_descriptors,
            max_arity=max_arity,
            require_effect_variation=False,
        )
    )
