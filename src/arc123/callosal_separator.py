"""Generic finite semantic-separator learning for Forward–Backward Singularity Learning.

The learner receives observations with a typed descriptor dictionary and an
observed effect.  Deterministic separator induction is formulated as an exact
bad-collision cover: every pair of observations carrying different effects must
be separated by at least one selected descriptor.  This is equivalent to the
older exhaustive-subset definition but exposes the true BCQ semantic width and
permits contradiction-directed fixed-parameter search.

Crucially, the learner returns the *fiber* of all equally minimum-description
deterministic separators rather than silently choosing one lexical
representative.  That is necessary when demonstrations do not identify one
semantic coordinate: ambiguity is retained until downstream prediction
singularity, not erased by a tie-break.

This is intentionally domain-independent: rows, objects, frames, transitions,
and ARC3 state/action records can all feed the same core once perception has
produced descriptors. It is complete relative to the supplied finite
descriptor vocabulary and configured maximum separator arity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Iterable, Mapping, Optional, Sequence

SemanticValue = Hashable
ConflictPair = tuple[int, int]


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
            # For a model returned by learn_minimal_separator[_fiber], arity is
            # exactly the local bad-collision-cover / BCQ separation width.
            "bcq_separation_width": self.arity,
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


def _effect_conflicts(observations: Sequence[SemanticObservation]) -> tuple[ConflictPair, ...]:
    """Pairs that must be separated for the forward map to be deterministic."""

    return tuple(
        (left, right)
        for left in range(len(observations))
        for right in range(left + 1, len(observations))
        if observations[left].effect != observations[right].effect
    )


def _descriptor_conflict_coverage(
    observations: Sequence[SemanticObservation],
    names: Sequence[str],
    conflicts: Sequence[ConflictPair],
) -> dict[str, frozenset[int]]:
    return {
        name: frozenset(
            conflict_index
            for conflict_index, (left, right) in enumerate(conflicts)
            if observations[left].descriptors[name] != observations[right].descriptors[name]
        )
        for name in names
    }


def _minimum_conflict_covers(
    observations: Sequence[SemanticObservation],
    names: Sequence[str],
    max_arity: int,
) -> tuple[tuple[str, ...], ...]:
    """Return every minimum-cardinality descriptor cover up to `max_arity`.

    A descriptor subset S yields a deterministic effect table iff, for each pair
    of observations with different effects, at least one descriptor in S has a
    different value on that pair.  Thus minimum separator arity is exactly a
    minimum hitting-set problem on effect-conflict pairs.

    Search branches on one currently uncovered contradiction and only on
    descriptors capable of repairing it.  Generic hitting set remains NP-hard,
    but this is fixed-parameter in the optimum separator arity (the local BCQ
    separation width) and avoids enumerating every k-subset of the vocabulary.
    """

    if max_arity < 1 or not names:
        return ()

    conflicts = _effect_conflicts(observations)
    if not conflicts:
        # Preserve historical semantics for require_effect_variation=False:
        # the learner returns the best arity-1 representation, not an empty key.
        return tuple((name,) for name in names)

    coverage = _descriptor_conflict_coverage(observations, names, conflicts)
    separators: list[tuple[str, ...]] = []
    for conflict_index in range(len(conflicts)):
        repairing = tuple(name for name in names if conflict_index in coverage[name])
        if not repairing:
            return ()
        separators.append(repairing)

    universe = frozenset(range(len(conflicts)))
    best_width = max_arity + 1
    solutions: set[frozenset[str]] = set()
    seen: set[frozenset[str]] = set()

    def search(selected: frozenset[str], covered: frozenset[int]) -> None:
        nonlocal best_width, solutions
        if len(selected) > max_arity or len(selected) > best_width:
            return
        if selected in seen:
            return
        seen.add(selected)
        if covered == universe:
            if len(selected) < best_width:
                best_width = len(selected)
                solutions = {selected}
            elif len(selected) == best_width:
                solutions.add(selected)
            return
        if len(selected) >= min(max_arity, best_width):
            return

        uncovered = universe - covered
        pivot = min(
            uncovered,
            key=lambda conflict_index: (
                len([name for name in separators[conflict_index] if name not in selected]),
                conflict_index,
            ),
        )
        branches = [name for name in separators[pivot] if name not in selected]
        branches.sort(
            key=lambda name: (
                -len(coverage[name] - covered),
                name,
            )
        )
        for name in branches:
            search(selected | frozenset((name,)), covered | coverage[name])

    search(frozenset(), frozenset())
    return tuple(
        sorted(
            (tuple(sorted(solution)) for solution in solutions),
            key=lambda subset: subset,
        )
    )


def separator_bcq_width(
    observations: Sequence[SemanticObservation],
    candidate_descriptors: Iterable[str] | None = None,
    *,
    max_arity: int | None = None,
) -> Optional[int]:
    """Return exact local BCQ separation width, or None if the language/cap fails."""

    if not observations:
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
    covers = _minimum_conflict_covers(observations, names, limit)
    return len(covers[0]) if covers else None


def learn_minimal_separator_fiber(
    observations: Sequence[SemanticObservation],
    candidate_descriptors: Iterable[str] | None = None,
    *,
    max_arity: int | None = None,
    require_effect_variation: bool = True,
) -> tuple[SeparatorModel, ...]:
    """Return every equally minimum-description exact separator.

    Minimum arity is found by exact contradiction-directed conflict-cover
    search. At that arity, all minimum covers are scored by table compression,
    repeated support, minimum support and semantic-domain encoding. Every subset
    tied at the optimal score is retained. Lexical order makes the returned
    tuple reproducible but does *not* erase the tie.

    If several semantic explanations remain observationally indistinguishable,
    downstream code can ask whether they nevertheless induce one prediction.
    It must not invent a unique latent program merely because one descriptor
    name sorts first.
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
    covers = _minimum_conflict_covers(observations, names, limit)
    if not covers:
        return ()

    viable: list[
        tuple[
            tuple[int, int, int, int],
            tuple[str, ...],
            dict[tuple[SemanticValue, ...], SemanticValue],
        ]
    ] = []
    for subset in covers:
        table = _deterministic_table(observations, subset)
        if table is None:
            # This would violate the conflict-cover equivalence theorem.
            raise AssertionError("conflict cover did not induce a deterministic table")
        viable.append((_score_subset(observations, subset, table), subset, table))

    best_score = min(item[0] for item in viable)
    tied = [item for item in viable if item[0] == best_score]
    models = []
    for _, subset, table in sorted(tied, key=lambda item: item[1]):
        rows = tuple(sorted(table.items(), key=lambda item: repr(item[0])))
        models.append(SeparatorModel(subset, rows))
    return tuple(models)


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
