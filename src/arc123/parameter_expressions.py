"""Small typed parameter-expression fibers for semantic program synthesis.

A structural transform can be correctly identified while one of its integer
parameters remains underdetermined by the demonstrations.  This module keeps
that ambiguity explicit instead of hard-wiring one statistic into a complete
ARC rule.

The first expression language maps a non-empty integer sequence to one integer.
All expressions below have equal primitive cost: if several fit every observed
world, all remain in the compatibility fiber.  A caller may collapse only when
their downstream predictions agree.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence


EvalFn = Callable[[tuple[int, ...]], Optional[int]]


@dataclass(frozen=True)
class IntegerSequenceExpression:
    name: str
    fn: EvalFn
    cost: int = 1

    def evaluate(self, values: Sequence[int]) -> Optional[int]:
        seq = tuple(int(value) for value in values)
        if not seq:
            return None
        return self.fn(seq)


def _order_desc(rank: int) -> IntegerSequenceExpression:
    return IntegerSequenceExpression(
        f"order_desc_{rank}",
        lambda xs, rank=rank: sorted(xs, reverse=True)[rank - 1]
        if len(xs) >= rank
        else None,
    )


def _order_asc(rank: int) -> IntegerSequenceExpression:
    return IntegerSequenceExpression(
        f"order_asc_{rank}",
        lambda xs, rank=rank: sorted(xs)[rank - 1] if len(xs) >= rank else None,
    )


def _floor_mean(xs: tuple[int, ...]) -> int:
    return sum(xs) // len(xs)


def _ceil_mean(xs: tuple[int, ...]) -> int:
    return (sum(xs) + len(xs) - 1) // len(xs)


def _floor_midrange(xs: tuple[int, ...]) -> int:
    return (min(xs) + max(xs)) // 2


def _ceil_midrange(xs: tuple[int, ...]) -> int:
    return (min(xs) + max(xs) + 1) // 2


def _median_low(xs: tuple[int, ...]) -> int:
    ordered = sorted(xs)
    return ordered[(len(ordered) - 1) // 2]


def _median_high(xs: tuple[int, ...]) -> int:
    ordered = sorted(xs)
    return ordered[len(ordered) // 2]


def default_integer_sequence_expressions(max_order_rank: int = 3) -> tuple[IntegerSequenceExpression, ...]:
    expressions: list[IntegerSequenceExpression] = [
        IntegerSequenceExpression("minimum", min),
        IntegerSequenceExpression("maximum", max),
        IntegerSequenceExpression("floor_mean", _floor_mean),
        IntegerSequenceExpression("ceil_mean", _ceil_mean),
        IntegerSequenceExpression("floor_midrange", _floor_midrange),
        IntegerSequenceExpression("ceil_midrange", _ceil_midrange),
        IntegerSequenceExpression("median_low", _median_low),
        IntegerSequenceExpression("median_high", _median_high),
    ]
    for rank in range(1, max_order_rank + 1):
        expressions.append(_order_desc(rank))
        expressions.append(_order_asc(rank))
    # Names are canonical identifiers; remove only literal duplicate names,
    # never expressions that happen to agree on the current observations.
    unique: dict[str, IntegerSequenceExpression] = {}
    for expression in expressions:
        unique.setdefault(expression.name, expression)
    return tuple(unique.values())


def compatible_integer_sequence_expression_fiber(
    observations: Sequence[tuple[Sequence[int], int]],
    expressions: Sequence[IntegerSequenceExpression] | None = None,
) -> tuple[IntegerSequenceExpression, ...]:
    """Return every minimum-cost expression compatible with all observations."""

    candidates = tuple(expressions or default_integer_sequence_expressions())
    compatible = [
        expression
        for expression in candidates
        if all(expression.evaluate(values) == int(target) for values, target in observations)
    ]
    if not compatible:
        return ()
    minimum_cost = min(expression.cost for expression in compatible)
    return tuple(
        sorted(
            (expression for expression in compatible if expression.cost == minimum_cost),
            key=lambda expression: expression.name,
        )
    )
