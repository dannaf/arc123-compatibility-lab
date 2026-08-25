"""Generic measurement-to-output-geometry hypotheses.

These productions treat a semantic measurement as a compact callosal state that
controls output geometry.  They are intentionally narrow: a candidate is
promoted only when the same measurement/render relation exactly explains every
training world.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .model import Grid, PartialGrid, TrainingPair
from .perceptions import background_color, connected_components


@dataclass(frozen=True)
class ComponentCountBlankColumn:
    """Render foreground-component cardinality as a one-column grid height.

    If the input contains k 4-connected non-background components, emit a
    one-column grid of height k+1 using the input background color.  The extra
    one is part of the learned production, not inferred from the held-out test.
    """

    name: str = "component_count_plus_one_blank_column"
    description_length: int = 5

    @property
    def callosal_summary(self) -> dict[str, object]:
        return {
            "interface": "foreground_component_count -> output_height",
            "measurement": "4_connected_nonbackground_components",
            "output_height": "component_count + 1",
            "output_width": 1,
            "output_value": "input_background",
            "forward_deterministic": True,
            "backward_semantics": "output height h constrains source to h-1 foreground components",
        }

    def predict(self, input_grid: Grid) -> Optional[PartialGrid]:
        if not input_grid or not input_grid[0]:
            return None
        background = background_color(input_grid)
        components = connected_components(input_grid)
        if not components:
            return None
        return tuple((background,) for _ in range(len(components) + 1))


def propose_measurement_hypotheses(
    training_pairs: Sequence[TrainingPair],
    enabled_operator_families: Sequence[str] | None = None,
) -> list[ComponentCountBlankColumn]:
    if enabled_operator_families is not None and (
        "component_count_plus_one_blank_column" not in enabled_operator_families
    ):
        return []
    if not training_pairs:
        return []
    candidate = ComponentCountBlankColumn()
    return [candidate] if all(
        candidate.predict(input_grid) == output_grid
        for input_grid, output_grid in training_pairs
    ) else []
