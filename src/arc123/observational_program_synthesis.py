"""Generic n-ary typed synthesis with observational quotienting.

This is the search engine needed once ARC programs become compositional enough
that naive syntax-tree enumeration explodes.

For a *current task*, two typed terms are observationally equivalent when they
produce identical semantic values on every training input and every current
test input.  Because downstream primitives are deterministic functions of
those values and the same root grid, equivalent terms remain equivalent under
all future compositions on this task.  We can therefore quotient them during
search without changing the set of possible current test predictions.

The held-out targets are never used to build the quotient.  Training outputs
are consulted only after search to identify exact complete Grid terms.

This module is grammar-agnostic: ARC semantic vocabularies register typed
n-ary primitives separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable, Hashable, Optional, Sequence

from .model import Grid, TrainingPair


TypeTag = str
SemanticValue = object
NaryFn = Callable[[tuple[SemanticValue, ...], Grid], Optional[SemanticValue]]


@dataclass(frozen=True)
class NaryPrimitive:
    name: str
    input_types: tuple[TypeTag, ...]
    output_type: TypeTag
    cost: int
    fn: NaryFn


@dataclass(frozen=True)
class Term:
    """One representative term of an observational equivalence class."""

    type_tag: TypeTag
    primitive: Optional[NaryPrimitive] = None
    children: tuple["Term", ...] = ()

    @property
    def name(self) -> str:
        if self.primitive is None:
            return "input"
        if not self.children:
            return self.primitive.name
        return f"{self.primitive.name}(" + ",".join(child.name for child in self.children) + ")"

    @property
    def cost(self) -> int:
        if self.primitive is None:
            return 0
        return self.primitive.cost + sum(child.cost for child in self.children)

    def evaluate(self, root: Grid) -> Optional[SemanticValue]:
        if self.primitive is None:
            return root
        values: list[SemanticValue] = []
        for child in self.children:
            value = child.evaluate(root)
            if value is None:
                return None
            values.append(value)
        return self.primitive.fn(tuple(values), root)


@dataclass(frozen=True)
class QuotientState:
    type_tag: TypeTag
    term: Term
    values: tuple[SemanticValue, ...]
    signature: tuple[Hashable, ...]
    equivalent_term_count: int = 1

    @property
    def cost(self) -> int:
        return self.term.cost


def _freeze(value: SemanticValue) -> Hashable:
    """Canonicalize common semantic values for quotient keys."""

    if value is None:
        return ("NONE",)
    if isinstance(value, (int, str, bool)):
        return value
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((_freeze(key), _freeze(item)) for key, item in value.items()))
    # ARC Component and other frozen dataclasses have stable repr/equality; repr
    # is a deterministic fallback for task-local observational quotienting.
    return (type(value).__name__, repr(value))


def _cost_partitions(total: int, arity: int) -> tuple[tuple[int, ...], ...]:
    if arity == 0:
        return ((),) if total == 0 else ()
    if arity == 1:
        return ((total,),)
    result: list[tuple[int, ...]] = []
    for first in range(total + 1):
        for rest in _cost_partitions(total - first, arity - 1):
            result.append((first, *rest))
    return tuple(result)


@dataclass(frozen=True)
class ObservationalSearchResult:
    states: tuple[QuotientState, ...]
    exact_grid_states: tuple[QuotientState, ...]
    exact_test_prediction_group_count: int
    generated_term_count: int
    quotient_state_count: int

    @property
    def has_prediction_singularity(self) -> bool:
        return bool(self.exact_grid_states) and self.exact_test_prediction_group_count == 1


def synthesize_observational_quotient(
    training_pairs: Sequence[TrainingPair],
    test_inputs: Sequence[Grid],
    primitives: Sequence[NaryPrimitive],
    *,
    root_type: TypeTag = "Grid",
    max_cost: int = 6,
) -> ObservationalSearchResult:
    """Bottom-up typed search quotiented on all observable input worlds.

    Terms undefined on any current training/test input are omitted from this
    complete-program search. Partial/UNKNOWN synthesis can be layered on later
    with a three-valued signature instead of silently converting undefined to
    a value.
    """

    roots = tuple(input_grid for input_grid, _ in training_pairs) + tuple(test_inputs)
    if not roots:
        return ObservationalSearchResult((), (), 0, 0, 0)

    root_term = Term(root_type)
    root_values: tuple[SemanticValue, ...] = roots
    root_signature = tuple(_freeze(value) for value in root_values)
    root_state = QuotientState(root_type, root_term, root_values, root_signature)

    # Lowest-cost quotient states. by_cost is required for exact-cost dynamic
    # programming and permits n-ary child combinations without recursive
    # syntax-tree enumeration.
    by_type_cost: dict[tuple[TypeTag, int], list[QuotientState]] = {(root_type, 0): [root_state]}
    best: dict[tuple[TypeTag, tuple[Hashable, ...]], QuotientState] = {
        (root_type, root_signature): root_state
    }
    generated_term_count = 0

    for total_cost in range(1, max_cost + 1):
        for primitive in primitives:
            child_budget = total_cost - primitive.cost
            if child_budget < 0:
                continue
            for partition in _cost_partitions(child_budget, len(primitive.input_types)):
                child_pools: list[list[QuotientState]] = []
                viable = True
                for type_tag, child_cost in zip(primitive.input_types, partition):
                    pool = by_type_cost.get((type_tag, child_cost), [])
                    if not pool:
                        viable = False
                        break
                    child_pools.append(pool)
                if not viable:
                    continue
                for children in product(*child_pools):
                    generated_term_count += 1
                    term = Term(primitive.output_type, primitive, tuple(child.term for child in children))
                    values: list[SemanticValue] = []
                    defined = True
                    for world_index, root in enumerate(roots):
                        args = tuple(child.values[world_index] for child in children)
                        value = primitive.fn(args, root)
                        if value is None:
                            defined = False
                            break
                        values.append(value)
                    if not defined:
                        continue
                    value_tuple = tuple(values)
                    signature = tuple(_freeze(value) for value in value_tuple)
                    key = (primitive.output_type, signature)
                    existing = best.get(key)
                    if existing is not None:
                        if existing.cost == total_cost:
                            best[key] = QuotientState(
                                existing.type_tag,
                                existing.term,
                                existing.values,
                                existing.signature,
                                existing.equivalent_term_count + 1,
                            )
                        continue
                    state = QuotientState(
                        primitive.output_type,
                        term,
                        value_tuple,
                        signature,
                    )
                    best[key] = state
                    by_type_cost.setdefault((primitive.output_type, total_cost), []).append(state)

    states = tuple(
        sorted(best.values(), key=lambda state: (state.cost, state.type_tag, state.term.name))
    )
    train_count = len(training_pairs)
    exact: list[QuotientState] = []
    for state in states:
        if state.type_tag != "Grid":
            continue
        if all(state.values[index] == training_pairs[index][1] for index in range(train_count)):
            exact.append(state)
    if exact:
        minimum_cost = min(state.cost for state in exact)
        exact = [state for state in exact if state.cost == minimum_cost]
    prediction_signatures = {
        tuple(_freeze(value) for value in state.values[train_count:])
        for state in exact
    }
    return ObservationalSearchResult(
        states=states,
        exact_grid_states=tuple(exact),
        exact_test_prediction_group_count=len(prediction_signatures),
        generated_term_count=generated_term_count,
        quotient_state_count=len(states),
    )
