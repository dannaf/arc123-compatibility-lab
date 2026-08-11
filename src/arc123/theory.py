"""Persistent partial theories, scoped rules, and observed residual bookkeeping."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional, Sequence

from .compatibility import evaluate_partial_prediction
from .contracts import CompatibilitySupport, HypothesisAction, Residual
from .hypotheses import Hypothesis
from .model import ActionKind, Counterexample, Grid, PartialGrid, SupportState, TrainingPair
from .perceptions import background_color, connected_components


Mask = tuple[tuple[bool, ...], ...]


def _blank_grid(height: int, width: int) -> list[list[Optional[int]]]:
    return [[None for _ in range(width)] for _ in range(height)]


def _freeze_partial(grid: Sequence[Sequence[Optional[int]]]) -> PartialGrid:
    return tuple(tuple(cell for cell in row) for row in grid)


def _freeze_mask(mask: Sequence[Sequence[bool]]) -> Mask:
    return tuple(tuple(cell for cell in row) for row in mask)


def _parameter_tuple(**parameters: int | str) -> tuple[tuple[str, int | str], ...]:
    return tuple(sorted(parameters.items()))


def _component_context(grid: Grid) -> dict[tuple[int, int], tuple[int, int, int]]:
    components = connected_components(grid, include_background=True)
    ranked = sorted(components, key=lambda item: (-item.area, item.color, item.bbox))
    context: dict[tuple[int, int], tuple[int, int, int]] = {}
    for rank, component in enumerate(ranked):
        for cell in component.cells:
            context[cell] = (component.color, component.area, rank)
    return context


@dataclass(frozen=True)
class ScopePredicate:
    """A generic input-derived rule scope, evaluated independently for each example."""

    kind: str = "all"
    value: int | str | None = None

    @classmethod
    def all(cls) -> "ScopePredicate":
        return cls("all")

    @classmethod
    def color(cls, color: int) -> "ScopePredicate":
        return cls("color_equals", color)

    def description(self) -> str:
        if self.kind == "all":
            return "all"
        if self.kind == "color_equals":
            return f"color=={self.value}"
        if self.kind == "component_area_equals":
            return f"component.area=={self.value}"
        if self.kind == "component_rank":
            return f"component.rank=={self.value}"
        if self.kind == "on_border":
            return "on_border"
        raise ValueError(f"unknown scope predicate kind: {self.kind}")

    def matches(
        self,
        grid: Grid,
        row: int,
        column: int,
        component_context: Mapping[tuple[int, int], tuple[int, int, int]],
    ) -> bool:
        if self.kind == "all":
            return True
        if self.kind == "color_equals":
            return grid[row][column] == self.value
        if self.kind == "component_area_equals":
            return component_context[(row, column)][1] == self.value
        if self.kind == "component_rank":
            return component_context[(row, column)][2] == self.value
        if self.kind == "on_border":
            return row in {0, len(grid) - 1} or column in {0, len(grid[0]) - 1}
        raise ValueError(f"unknown scope predicate kind: {self.kind}")

    def as_dict(self) -> dict[str, int | str | None]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True)
class TheoryRule:
    """An ordered generic rule whose writes are explicit and inspectable."""

    rule_id: str
    operation: str
    scope: ScopePredicate = ScopePredicate.all()
    parameters: tuple[tuple[str, int | str], ...] = ()
    description_length: int = 1

    @classmethod
    def identity(cls, rule_id: str = "identity") -> "TheoryRule":
        return cls(rule_id=rule_id, operation="identity", description_length=1)

    @classmethod
    def full_operator(cls, rule_id: str, hypothesis: Hypothesis) -> "TheoryRule":
        parameters = (("operator", hypothesis.kind), *hypothesis.parameters)
        return cls(
            rule_id=rule_id,
            operation="full_operator",
            parameters=tuple(parameters),
            description_length=hypothesis.description_length,
        )

    @property
    def parameter_map(self) -> dict[str, int | str]:
        return dict(self.parameters)

    @property
    def name(self) -> str:
        parameters = self.parameter_map
        if self.operation == "identity":
            return "identity"
        if self.operation == "full_operator":
            operator = str(parameters["operator"])
            operator_parameters = tuple(
                (key, value) for key, value in self.parameters if key != "operator"
            )
            return Hypothesis(operator, operator_parameters, self.description_length).name
        if self.operation == "coordinate_transform":
            return f"{parameters['axis']}(scope={self.scope.description()})"
        if self.operation == "recolor_scoped":
            return f"recolor(to={parameters['to_color']},scope={self.scope.description()})"
        if self.operation == "environment_transition":
            return f"environment_transition(effect={parameters['effect']})"
        raise ValueError(f"unknown theory operation: {self.operation}")

    def with_scope(self, scope: ScopePredicate) -> "TheoryRule":
        return replace(self, scope=scope)

    def with_parameter(self, name: str, value: int | str) -> "TheoryRule":
        parameters = self.parameter_map
        parameters[name] = value
        return replace(self, parameters=tuple(sorted(parameters.items())))

    def without_parameter(self, name: str) -> "TheoryRule":
        return replace(
            self,
            parameters=tuple((key, value) for key, value in self.parameters if key != name),
        )

    def writes(self, input_grid: Grid) -> dict[tuple[int, int], int]:
        height = len(input_grid)
        width = len(input_grid[0])
        if self.operation == "identity":
            return {
                (row, column): input_grid[row][column]
                for row in range(height)
                for column in range(width)
            }
        if self.operation == "full_operator":
            prediction = self.full_prediction(input_grid)
            if prediction is None:
                return {}
            return {
                (row, column): int(color)
                for row, prediction_row in enumerate(prediction)
                for column, color in enumerate(prediction_row)
                if color is not None
            }
        if self.operation == "environment_transition":
            return {}
        component_context = _component_context(input_grid)
        selected = [
            (row, column)
            for row in range(height)
            for column in range(width)
            if self.scope.matches(input_grid, row, column, component_context)
        ]
        if self.operation == "recolor_scoped":
            color = int(self.parameter_map["to_color"])
            return {(row, column): color for row, column in selected}
        if self.operation != "coordinate_transform":
            raise ValueError(f"unknown theory operation: {self.operation}")
        axis = str(self.parameter_map["axis"])
        transforms = {
            "left_right": lambda row, column: (row, width - 1 - column),
            "top_bottom": lambda row, column: (height - 1 - row, column),
            "rotate_180": lambda row, column: (height - 1 - row, width - 1 - column),
        }
        if axis not in transforms:
            raise ValueError(f"unknown coordinate transform axis: {axis}")
        transform = transforms[axis]
        writes: dict[tuple[int, int], int] = {}
        if self.scope.kind != "all":
            background = background_color(input_grid)
            for row, column in selected:
                writes[(row, column)] = background
        for row, column in selected:
            writes[transform(row, column)] = input_grid[row][column]
        return writes

    def full_prediction(self, input_grid: Grid) -> Optional[PartialGrid]:
        if self.operation != "full_operator":
            return None
        parameters = self.parameter_map
        operator = str(parameters["operator"])
        operator_parameters = tuple(
            (key, value) for key, value in self.parameters if key != "operator"
        )
        return Hypothesis(operator, operator_parameters, self.description_length).predict(input_grid)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "operation": self.operation,
            "name": self.name,
            "scope": self.scope.as_dict(),
            "parameters": dict(self.parameters),
            "description_length": self.description_length,
        }


@dataclass(frozen=True)
class TheoryDemoEvidence:
    """Current-theory prediction and residual state for one explicitly inspected demo."""

    demo_index: int
    partial_prediction: PartialGrid
    composed_prediction: PartialGrid
    explained_mask: Mask
    residual_mask: Mask
    support: CompatibilitySupport
    residuals: tuple[Residual, ...]
    counterexamples: tuple[Counterexample, ...]
    responsible_rule_ids: tuple[str | None, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "demo_index": self.demo_index,
            "partial_prediction": [list(row) for row in self.partial_prediction],
            "composed_prediction": [list(row) for row in self.composed_prediction],
            "explained_cell_count": sum(sum(row) for row in self.explained_mask),
            "residual_cell_count": sum(sum(row) for row in self.residual_mask),
            "support": self.support.as_dict(),
            "residuals": [item.as_dict() for item in self.residuals],
            "counterexamples": [item.as_dict() for item in self.counterexamples],
            "responsible_rule_ids": list(self.responsible_rule_ids),
        }


def _render_rules(
    rules: Sequence[TheoryRule], input_grid: Grid, include_identity: bool
) -> tuple[PartialGrid, tuple[tuple[str | None, ...], ...]]:
    height = len(input_grid)
    width = len(input_grid[0])
    canvas = _blank_grid(height, width)
    claims: list[list[str | None]] = [[None for _ in range(width)] for _ in range(height)]
    for rule in rules:
        if not include_identity and rule.operation == "identity":
            continue
        full_prediction = rule.full_prediction(input_grid)
        if full_prediction is not None:
            next_height = len(full_prediction)
            next_width = len(full_prediction[0])
            if (next_height, next_width) != (len(canvas), len(canvas[0])):
                canvas = _blank_grid(next_height, next_width)
                claims = [[None for _ in range(next_width)] for _ in range(next_height)]
            for row, prediction_row in enumerate(full_prediction):
                for column, color in enumerate(prediction_row):
                    if color is not None:
                        canvas[row][column] = color
                        claims[row][column] = rule.rule_id
            continue
        writes = rule.writes(input_grid)
        for (row, column), color in writes.items():
            if 0 <= row < height and 0 <= column < width:
                canvas[row][column] = color
                claims[row][column] = rule.rule_id
    return _freeze_partial(canvas), tuple(tuple(row) for row in claims)


def _all_counterexamples(
    demo_index: int, prediction: PartialGrid, observed_output: Grid
) -> tuple[Counterexample, ...]:
    if len(prediction) != len(observed_output) or any(
        len(prediction_row) != len(observed_row)
        for prediction_row, observed_row in zip(prediction, observed_output)
    ):
        return ()
    return tuple(
        Counterexample(demo_index, row, column, int(predicted), observed)
        for row, (prediction_row, observed_row) in enumerate(zip(prediction, observed_output))
        for column, (predicted, observed) in enumerate(zip(prediction_row, observed_row))
        if predicted is not None and predicted != observed
    )


def evaluate_theory_demo(
    theory: "PartialTheory", demo_index: int, input_grid: Grid, observed_output: Grid
) -> TheoryDemoEvidence:
    partial_prediction, _ = _render_rules(theory.rules, input_grid, include_identity=False)
    composed_prediction, claims = _render_rules(theory.rules, input_grid, include_identity=True)
    feedback = evaluate_partial_prediction(demo_index, composed_prediction, observed_output)
    all_counterexamples = _all_counterexamples(demo_index, composed_prediction, observed_output)
    explained = [
        [False for _ in range(len(observed_output[0]))] for _ in range(len(observed_output))
    ]
    residual = [
        [False for _ in range(len(observed_output[0]))] for _ in range(len(observed_output))
    ]
    contradictory_cells: list[tuple[int, int]] = []
    contradictory_predicted: list[int | None] = []
    contradictory_observed: list[int] = []
    unknown_cells: list[tuple[int, int]] = []
    for row, observed_row in enumerate(observed_output):
        for column, observed in enumerate(observed_row):
            predicted = (
                composed_prediction[row][column]
                if row < len(composed_prediction) and column < len(composed_prediction[row])
                else None
            )
            if predicted is not None and predicted == observed:
                explained[row][column] = True
            else:
                residual[row][column] = True
                if predicted is None:
                    unknown_cells.append((row, column))
                else:
                    contradictory_cells.append((row, column))
                    contradictory_predicted.append(predicted)
                    contradictory_observed.append(observed)
    residuals: list[Residual] = []
    if contradictory_cells:
        residuals.append(
            Residual(
                observation_id=f"arc12-demo:{demo_index}",
                residual_kind="contradiction",
                cells=tuple(contradictory_cells),
                predicted_values=tuple(contradictory_predicted),
                observed_values=tuple(contradictory_observed),
            )
        )
    if unknown_cells:
        residuals.append(
            Residual(
                observation_id=f"arc12-demo:{demo_index}",
                residual_kind="unknown",
                cells=tuple(unknown_cells),
            )
        )
    support = CompatibilitySupport(
        observation_id=f"arc12-demo:{demo_index}",
        support_state=feedback.support_state,
        asserted_cell_count=feedback.asserted_cell_count,
        matching_cell_count=feedback.matching_cell_count,
        contradiction_count=feedback.contradiction_count,
        unknown_cell_count=feedback.unknown_cell_count,
        counterexamples=feedback.counterexamples,
    )
    responsible = tuple(
        claims[counterexample.row][counterexample.column]
        for counterexample in all_counterexamples
    )
    return TheoryDemoEvidence(
        demo_index=demo_index,
        partial_prediction=partial_prediction,
        composed_prediction=composed_prediction,
        explained_mask=_freeze_mask(explained),
        residual_mask=_freeze_mask(residual),
        support=support,
        residuals=tuple(residuals),
        counterexamples=all_counterexamples,
        responsible_rule_ids=responsible,
    )


@dataclass(frozen=True)
class PartialTheory:
    """A persistent, revisable rule set with current observed support and residual state."""

    theory_id: str
    parent_theory_id: str | None
    rules: tuple[TheoryRule, ...]
    parameter_bindings: tuple[tuple[str, int | str], ...] = ()
    scope_predicates: tuple[ScopePredicate, ...] = ()
    demo_evidence: tuple[TheoryDemoEvidence, ...] = ()
    counterexamples: tuple[Counterexample, ...] = ()
    unresolved_unknown: tuple[Residual, ...] = ()
    history: tuple[HypothesisAction, ...] = ()

    @classmethod
    def root(cls, theory_id: str = "T0000") -> "PartialTheory":
        return cls(theory_id=theory_id, parent_theory_id=None, rules=())

    @property
    def description_length(self) -> int:
        return sum(rule.description_length for rule in self.rules)

    @property
    def name(self) -> str:
        if len(self.rules) == 1:
            return self.rules[0].name
        if not self.rules:
            return "empty_theory"
        return "compose(" + ",".join(rule.name for rule in self.rules) + ")"

    @property
    def evaluated_demo_indices(self) -> tuple[int, ...]:
        return tuple(item.demo_index for item in self.demo_evidence)

    @property
    def matching_cell_count(self) -> int:
        return sum(item.support.matching_cell_count for item in self.demo_evidence)

    @property
    def contradiction_count(self) -> int:
        return sum(item.support.contradiction_count for item in self.demo_evidence)

    @property
    def unknown_cell_count(self) -> int:
        return sum(item.support.unknown_cell_count for item in self.demo_evidence)

    @property
    def is_compatible_on_observed(self) -> bool:
        return self.contradiction_count == 0

    @property
    def is_exact_on_observed(self) -> bool:
        return self.contradiction_count == 0 and self.unknown_cell_count == 0

    def priority(self) -> tuple[int, int, int, int, str]:
        return (
            self.contradiction_count,
            self.unknown_cell_count,
            -self.matching_cell_count,
            self.description_length,
            self.theory_id,
        )

    def predict(self, input_grid: Grid) -> PartialGrid:
        prediction, _ = _render_rules(self.rules, input_grid, include_identity=True)
        return prediction

    def add_demo_evidence(self, evidence: TheoryDemoEvidence, action: HypothesisAction) -> "PartialTheory":
        existing = {item.demo_index: item for item in self.demo_evidence}
        existing[evidence.demo_index] = evidence
        ordered = tuple(existing[index] for index in sorted(existing))
        counterexamples = tuple(
            counterexample for item in ordered for counterexample in item.counterexamples
        )
        unresolved = tuple(
            residual
            for item in ordered
            for residual in item.residuals
            if residual.residual_kind == "unknown"
        )
        return replace(
            self,
            demo_evidence=ordered,
            counterexamples=counterexamples,
            unresolved_unknown=unresolved,
            history=(*self.history, action),
        )

    def evolve(
        self,
        theory_id: str,
        action: HypothesisAction,
        *,
        rules: Sequence[TheoryRule] | None = None,
        parameter_bindings: Sequence[tuple[str, int | str]] | None = None,
    ) -> "PartialTheory":
        next_rules = tuple(rules if rules is not None else self.rules)
        return PartialTheory(
            theory_id=theory_id,
            parent_theory_id=self.theory_id,
            rules=next_rules,
            parameter_bindings=tuple(
                parameter_bindings if parameter_bindings is not None else self.parameter_bindings
            ),
            scope_predicates=tuple(rule.scope for rule in next_rules),
            history=(*self.history, action),
        )

    def add_rule(
        self, theory_id: str, rule: TheoryRule, action: HypothesisAction
    ) -> "PartialTheory":
        return self.evolve(theory_id, action, rules=(*self.rules, rule))

    def change_scope(
        self,
        theory_id: str,
        rule_id: str,
        scope: ScopePredicate,
        action: HypothesisAction,
    ) -> "PartialTheory":
        return self.evolve(
            theory_id,
            action,
            rules=tuple(
                rule.with_scope(scope) if rule.rule_id == rule_id else rule for rule in self.rules
            ),
        )

    def bind_parameter(
        self, theory_id: str, name: str, value: int | str, action: HypothesisAction
    ) -> "PartialTheory":
        bindings = dict(self.parameter_bindings)
        bindings[name] = value
        return self.evolve(theory_id, action, parameter_bindings=tuple(sorted(bindings.items())))

    def unbind_parameter(
        self, theory_id: str, name: str, action: HypothesisAction
    ) -> "PartialTheory":
        return self.evolve(
            theory_id,
            action,
            parameter_bindings=tuple(
                (key, value) for key, value in self.parameter_bindings if key != name
            ),
        )

    def reorder_rules(
        self, theory_id: str, rule_ids: Sequence[str], action: HypothesisAction
    ) -> "PartialTheory":
        ordered = {rule.rule_id: rule for rule in self.rules}
        if set(rule_ids) != set(ordered):
            raise ValueError("rule reorder must include every existing rule exactly once")
        return self.evolve(theory_id, action, rules=tuple(ordered[rule_id] for rule_id in rule_ids))

    def as_dict(self, include_predictions: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "theory_id": self.theory_id,
            "parent_theory_id": self.parent_theory_id,
            "name": self.name,
            "description_length": self.description_length,
            "rules": [rule.as_dict() for rule in self.rules],
            "parameter_bindings": dict(self.parameter_bindings),
            "scope_predicates": [scope.as_dict() for scope in self.scope_predicates],
            "evaluated_demo_indices": list(self.evaluated_demo_indices),
            "matching_cell_count": self.matching_cell_count,
            "contradiction_count": self.contradiction_count,
            "unknown_cell_count": self.unknown_cell_count,
            "counterexamples": [item.as_dict() for item in self.counterexamples],
            "unresolved_unknown": [item.as_dict() for item in self.unresolved_unknown],
            "history": [item.as_dict() for item in self.history],
        }
        if include_predictions:
            payload["demo_evidence"] = [item.as_dict() for item in self.demo_evidence]
        return payload

    def trace_summary(self) -> dict[str, Any]:
        """Return a non-duplicative state snapshot for repeated trace compare events."""

        return {
            "theory_id": self.theory_id,
            "parent_theory_id": self.parent_theory_id,
            "name": self.name,
            "description_length": self.description_length,
            "rules": [rule.as_dict() for rule in self.rules],
            "parameter_bindings": dict(self.parameter_bindings),
            "scope_predicates": [scope.as_dict() for scope in self.scope_predicates],
            "evaluated_demo_indices": list(self.evaluated_demo_indices),
            "matching_cell_count": self.matching_cell_count,
            "contradiction_count": self.contradiction_count,
            "unknown_cell_count": self.unknown_cell_count,
            "counterexample_count": len(self.counterexamples),
            "unresolved_unknown_count": len(self.unresolved_unknown),
            "revision_count": len(self.history),
        }


LearnerState = PartialTheory


def coordinate_transform_rule(
    rule_id: str, axis: str, scope: ScopePredicate = ScopePredicate.all()
) -> TheoryRule:
    return TheoryRule(
        rule_id=rule_id,
        operation="coordinate_transform",
        scope=scope,
        parameters=_parameter_tuple(axis=axis),
        description_length=2 if scope.kind == "all" else 3,
    )


def recolor_scoped_rule(rule_id: str, scope: ScopePredicate, to_color: int) -> TheoryRule:
    return TheoryRule(
        rule_id=rule_id,
        operation="recolor_scoped",
        scope=scope,
        parameters=_parameter_tuple(to_color=to_color),
        description_length=2,
    )
