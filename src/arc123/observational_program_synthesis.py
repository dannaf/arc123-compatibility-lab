"""Generic n-ary typed synthesis with observational quotienting.

This is the search engine needed once ARC programs become compositional enough
that naive syntax-tree enumeration explodes.

For a *current task*, two typed terms are observationally equivalent when they
produce identical semantic values on every training input and every current
test input.  Because downstream primitives are deterministic functions of
those values and the same root grid, equivalent terms remain equivalent under
all future compositions on this task.  We can therefore quotient them during
search without changing the set of possible current test predictions.

The held-out targets are never used to build the quotient. Training outputs
are consulted only after search to identify exact complete Grid terms.

Program cost is a DAG cost: a structurally identical subexpression used by two
branches is paid for once. This matters for programs such as

    ceil_half(add_ints(min(segment_lengths(x)), max(segment_lengths(x))))

where `segment_lengths(x)` is a shared semantic computation rather than two
independent pieces of evidence.
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
    def structural_key(self) -> Hashable:
        if self.primitive is None:
            return ("input", self.type_tag)
        return (
            self.primitive.name,
            self.type_tag,
            tuple(child.structural_key for child in self.children),
        )

    def _unique_primitive_nodes(self, nodes: dict[Hashable, int]) -> None:
        if self.primitive is None:
            return
        key = self.structural_key
        nodes.setdefault(key, self.primitive.cost)
        for child in self.children:
            child._unique_primitive_nodes(nodes)

    @property
    def cost(self) -> int:
        """Cost of the canonical computation DAG, sharing identical subterms."""

        nodes: dict[Hashable, int] = {}
        self._unique_primitive_nodes(nodes)
        return sum(nodes.values())

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
    return (type(value).__name__, repr(value))


@dataclass(frozen=True)
class ObservationalSearchResult:
    states: tuple[QuotientState, ...]
    exact_grid_states: tuple[QuotientState, ...]
    exact_test_prediction_group_count: int
    generated_term_count: int
    quotient_state_count: int
    minimum_exact_cost: Optional[int]

    @property
    def has_prediction_singularity(self) -> bool:
        return bool(self.exact_grid_states) and self.exact_test_prediction_group_count == 1


def _states_of_type_below_cost(
    by_type_cost: dict[tuple[TypeTag, int], list[QuotientState]],
    type_tag: TypeTag,
    max_child_cost: int,
) -> list[QuotientState]:
    result: list[QuotientState] = []
    for cost in range(max_child_cost + 1):
        result.extend(by_type_cost.get((type_tag, cost), ()))
    return result


def synthesize_observational_quotient(
    training_pairs: Sequence[TrainingPair],
    test_inputs: Sequence[Grid],
    primitives: Sequence[NaryPrimitive],
    *,
    root_type: TypeTag = "Grid",
    max_cost: int = 6,
) -> ObservationalSearchResult:
    """Bottom-up typed search quotiented on all observable input worlds.

    Search proceeds by exact DAG cost. Child pools may have a summed cost above
    the current budget because they can share subexpressions; the assembled
    term's actual DAG cost is computed before admission.

    Terms undefined on any current training/test input are omitted from this
    complete-program search. Partial/UNKNOWN synthesis can be layered on later
    with a three-valued signature instead of silently converting undefined to
    a value.
    """

    roots = tuple(input_grid for input_grid, _ in training_pairs) + tuple(test_inputs)
    if not roots:
        return ObservationalSearchResult((), (), 0, 0, 0, None)

    root_term = Term(root_type)
    root_values: tuple[SemanticValue, ...] = roots
    root_signature = tuple(_freeze(value) for value in root_values)
    root_state = QuotientState(root_type, root_term, root_values, root_signature)

    by_type_cost: dict[tuple[TypeTag, int], list[QuotientState]] = {(root_type, 0): [root_state]}
    best: dict[tuple[TypeTag, tuple[Hashable, ...]], QuotientState] = {
        (root_type, root_signature): root_state
    }
    generated_term_count = 0

    for total_cost in range(1, max_cost + 1):
        for primitive in primitives:
            if primitive.cost > total_cost:
                continue
            # Any child whose own DAG cost already reaches total_cost cannot
            # participate in a new positive-cost parent of this exact cost.
            child_pools = [
                _states_of_type_below_cost(by_type_cost, type_tag, total_cost - primitive.cost)
                for type_tag in primitive.input_types
            ]
            if any(not pool for pool in child_pools):
                continue
            for children in product(*child_pools):
                generated_term_count += 1
                term = Term(primitive.output_type, primitive, tuple(child.term for child in children))
                if term.cost != total_cost:
                    continue
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
                    # The quotient's canonical representative is the first
                    # lowest-cost derivation. Equivalent syntax does not create
                    # another semantic state or prediction branch.
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
    exact = [
        state
        for state in states
        if state.type_tag == "Grid"
        and all(state.values[index] == training_pairs[index][1] for index in range(train_count))
    ]
    minimum_exact_cost = min((state.cost for state in exact), default=None)
    # Strict singularity is over every represented exact program within the
    # declared search bound, not only an MDL-minimum subset. Complexity can
    # guide search order but cannot erase an exact incompatible prediction.
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
        minimum_exact_cost=minimum_exact_cost,
    )
