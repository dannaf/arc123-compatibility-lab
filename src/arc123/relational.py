"""Generic connected-component relations inferred from visible ARC examples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from .model import Grid, TrainingPair
from .perceptions import Component, background_color, connected_components


def _same_shape(input_grid: Grid, output_grid: Grid) -> bool:
    return len(input_grid) == len(output_grid) and len(input_grid[0]) == len(output_grid[0])


def canonical_component_shape(component: Component) -> str:
    """Encode a component mask independently of color and absolute position."""

    min_row, min_column, _, _ = component.bbox
    return ";".join(
        f"{row - min_row},{column - min_column}" for row, column in component.cells
    )


def component_symmetry_class(component: Component) -> str:
    """Return the component's axial symmetry class in its normalized bounding box."""

    min_row, min_column, max_row, max_column = component.bbox
    cells = {(row - min_row, column - min_column) for row, column in component.cells}
    height = max_row - min_row + 1
    width = max_column - min_column + 1
    horizontal = {(row, width - 1 - column) for row, column in cells} == cells
    vertical = {(height - 1 - row, column) for row, column in cells} == cells
    if horizontal and vertical:
        return "both"
    if horizontal:
        return "horizontal"
    if vertical:
        return "vertical"
    return "none"


def component_property(component: Component, property_name: str) -> str:
    if property_name == "shape":
        return canonical_component_shape(component)
    if property_name == "symmetry":
        return component_symmetry_class(component)
    raise ValueError(f"unknown component property: {property_name}")


def serialize_mapping(mapping: Sequence[tuple[str, int]]) -> str:
    return json.dumps(list(mapping), separators=(",", ":"), ensure_ascii=True)


def deserialize_mapping(serialized: str) -> dict[str, int]:
    raw_mapping = json.loads(serialized)
    if not isinstance(raw_mapping, list):
        raise ValueError("component relation mapping must be a list")
    result: dict[str, int] = {}
    for item in raw_mapping:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], int)
        ):
            raise ValueError("component relation mapping entry is malformed")
        result[item[0]] = item[1]
    return result


@dataclass(frozen=True)
class ComponentPropertyRecolorSpec:
    property_name: str
    mapping: tuple[tuple[str, int], ...]

    @property
    def mapping_json(self) -> str:
        return serialize_mapping(self.mapping)


@dataclass(frozen=True)
class ComponentPropertyEraseSpec:
    property_name: str
    values: tuple[str, ...]

    @property
    def mapping_json(self) -> str:
        return serialize_mapping(tuple((value, 0) for value in self.values))


@dataclass(frozen=True)
class MarkerShapeTargetRecolorSpec:
    marker_color: int
    target_color: int
    mapping: tuple[tuple[str, int], ...]

    @property
    def mapping_json(self) -> str:
        return serialize_mapping(self.mapping)


def _component_output_color(component: Component, output_grid: Grid) -> int | None:
    output_colors = {output_grid[row][column] for row, column in component.cells}
    if len(output_colors) != 1:
        return None
    return next(iter(output_colors))


def infer_component_property_recolor_specs(
    training_pairs: Sequence[TrainingPair],
) -> tuple[ComponentPropertyRecolorSpec, ...]:
    """Infer partial component recolors while leaving unmatched components untouched."""

    if len(training_pairs) < 2 or any(
        not _same_shape(input_grid, output_grid) for input_grid, output_grid in training_pairs
    ):
        return ()
    specifications: list[ComponentPropertyRecolorSpec] = []
    for property_name in ("shape", "symmetry"):
        mapping: dict[str, int] = {}
        observations: list[tuple[Component, int, int]] = []
        valid = True
        for input_grid, output_grid in training_pairs:
            input_background = background_color(input_grid)
            for component in connected_components(input_grid):
                output_color = _component_output_color(component, output_grid)
                if output_color is None:
                    valid = False
                    break
                observations.append((component, output_color, input_background))
                if output_color == input_background and component.color != input_background:
                    continue
                property_value = component_property(component, property_name)
                if output_color != component.color:
                    previous = mapping.get(property_value)
                    if previous is not None and previous != output_color:
                        valid = False
                        break
                    mapping[property_value] = output_color
            if not valid:
                break
        if not valid or not mapping:
            continue
        for component, output_color, input_background in observations:
            if output_color == input_background and component.color != input_background:
                continue
            property_value = component_property(component, property_name)
            expected = mapping.get(property_value, component.color)
            if output_color != expected:
                valid = False
                break
        if valid:
            specifications.append(
                ComponentPropertyRecolorSpec(
                    property_name=property_name,
                    mapping=tuple(sorted(mapping.items())),
                )
            )
    return tuple(specifications)


def infer_component_property_erase_specs(
    training_pairs: Sequence[TrainingPair],
) -> tuple[ComponentPropertyEraseSpec, ...]:
    """Infer component properties that consistently erase to each input's background."""

    if len(training_pairs) < 2 or any(
        not _same_shape(input_grid, output_grid) for input_grid, output_grid in training_pairs
    ):
        return ()
    specifications: list[ComponentPropertyEraseSpec] = []
    for property_name in ("shape", "symmetry"):
        erased_properties: set[str] = set()
        retained_properties: set[str] = set()
        valid = True
        for input_grid, output_grid in training_pairs:
            input_background = background_color(input_grid)
            for component in connected_components(input_grid):
                output_color = _component_output_color(component, output_grid)
                if output_color is None:
                    valid = False
                    break
                property_value = component_property(component, property_name)
                if output_color == input_background and component.color != input_background:
                    erased_properties.add(property_value)
                else:
                    retained_properties.add(property_value)
            if not valid:
                break
        values = erased_properties - retained_properties
        if valid and values:
            specifications.append(
                ComponentPropertyEraseSpec(
                    property_name=property_name,
                    values=tuple(sorted(values)),
                )
            )
    return tuple(specifications)


def component_property_recolor_writes(
    input_grid: Grid, property_name: str, mapping_json: str
) -> dict[tuple[int, int], int]:
    mapping = deserialize_mapping(mapping_json)
    writes: dict[tuple[int, int], int] = {}
    for component in connected_components(input_grid):
        output_color = mapping.get(component_property(component, property_name))
        if output_color is None:
            continue
        writes.update({cell: output_color for cell in component.cells})
    return writes


def component_property_erase_writes(
    input_grid: Grid, property_name: str, mapping_json: str
) -> dict[tuple[int, int], int]:
    property_values = set(deserialize_mapping(mapping_json))
    background = background_color(input_grid)
    return {
        cell: background
        for component in connected_components(input_grid)
        if component_property(component, property_name) in property_values
        for cell in component.cells
    }


def infer_marker_shape_target_recolor_specs(
    training_pairs: Sequence[TrainingPair],
) -> tuple[MarkerShapeTargetRecolorSpec, ...]:
    """Infer a color table keyed by an erased marker component's visible shape."""

    if len(training_pairs) < 2 or any(
        not _same_shape(input_grid, output_grid) for input_grid, output_grid in training_pairs
    ):
        return ()
    candidate_colors = set.intersection(
        *[
            {
                color
                for row in input_grid
                for color in row
                if color != background_color(input_grid)
            }
            for input_grid, _ in training_pairs
        ]
    )
    specifications: list[MarkerShapeTargetRecolorSpec] = []
    for marker_color in sorted(candidate_colors):
        for target_color in sorted(candidate_colors - {marker_color}):
            mapping: dict[str, int] = {}
            valid = True
            for input_grid, output_grid in training_pairs:
                marker_components = [
                    component
                    for component in connected_components(input_grid, connectivity=8)
                    if component.color == marker_color
                ]
                if len(marker_components) != 1:
                    valid = False
                    break
                marker_component = marker_components[0]
                if any(
                    output_grid[row][column] != background_color(input_grid)
                    for row, column in marker_component.cells
                ):
                    valid = False
                    break
                target_cells = [
                    (row, column)
                    for row, input_row in enumerate(input_grid)
                    for column, color in enumerate(input_row)
                    if color == target_color
                ]
                target_outputs = {output_grid[row][column] for row, column in target_cells}
                if not target_cells or len(target_outputs) != 1:
                    valid = False
                    break
                output_color = next(iter(target_outputs))
                if output_color == target_color:
                    valid = False
                    break
                signature = canonical_component_shape(marker_component)
                previous = mapping.get(signature)
                if previous is not None and previous != output_color:
                    valid = False
                    break
                mapping[signature] = output_color
            if valid and len(mapping) >= 2:
                specifications.append(
                    MarkerShapeTargetRecolorSpec(
                        marker_color=marker_color,
                        target_color=target_color,
                        mapping=tuple(sorted(mapping.items())),
                    )
                )
    return tuple(specifications)


def marker_shape_target_recolor_writes(
    input_grid: Grid,
    marker_color: int,
    target_color: int,
    mapping_json: str,
) -> dict[tuple[int, int], int]:
    marker_components = [
        component
        for component in connected_components(input_grid, connectivity=8)
        if component.color == marker_color
    ]
    if len(marker_components) != 1:
        return {}
    output_color = deserialize_mapping(mapping_json).get(
        canonical_component_shape(marker_components[0])
    )
    if output_color is None:
        return {}
    return {
        (row, column): output_color
        for row, input_row in enumerate(input_grid)
        for column, color in enumerate(input_row)
        if color == target_color
    }


def erase_color_to_background_writes(
    input_grid: Grid, source_color: int
) -> dict[tuple[int, int], int]:
    background = background_color(input_grid)
    return {
        (row, column): background
        for row, input_row in enumerate(input_grid)
        for column, color in enumerate(input_row)
        if color == source_color
    }
