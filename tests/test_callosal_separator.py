from itertools import combinations, product

from arc123.callosal_separator import (
    SemanticObservation,
    learn_minimal_separator,
    separator_bcq_width,
    separator_exists,
)


def test_row_marker_example_discovers_marker_column_not_row_or_color():
    observations = [
        SemanticObservation({"row": 0, "marker_column": 2, "marker_color": 5}, 3),
        SemanticObservation({"row": 1, "marker_column": 1, "marker_color": 5}, 4),
        SemanticObservation({"row": 2, "marker_column": 0, "marker_color": 5}, 2),
        SemanticObservation({"row": 0, "marker_column": 1, "marker_color": 5}, 4),
        SemanticObservation({"row": 1, "marker_column": 0, "marker_color": 5}, 2),
        SemanticObservation({"row": 2, "marker_column": 2, "marker_color": 5}, 3),
    ]
    model = learn_minimal_separator(observations)
    assert model is not None
    assert model.descriptor_names == ("marker_column",)
    assert model.predict({"row": 99, "marker_column": 1, "marker_color": 9}) == 4
    assert model.predict({"marker_column": 7}) is None  # unsupported key remains UNKNOWN
    assert model.backward_deterministic
    assert model.callosal_summary["bcq_separation_width"] == 1


def test_rectangle_examples_discover_interior_area_over_frame_color():
    observations = [
        SemanticObservation({"frame_color": 4, "interior_area": 1, "height": 3}, 5),
        SemanticObservation({"frame_color": 2, "interior_area": 2, "height": 3}, 7),
        SemanticObservation({"frame_color": 3, "interior_area": 2, "height": 4}, 7),
        SemanticObservation({"frame_color": 8, "interior_area": 1, "height": 3}, 5),
    ]
    model = learn_minimal_separator(observations)
    assert model is not None
    assert model.descriptor_names == ("interior_area",)
    assert model.predict({"frame_color": 9, "interior_area": 2, "height": 8}) == 7


def test_cross_object_bridge_discovers_controller_orientation():
    observations = [
        SemanticObservation(
            {"source_color": 8, "controller_color": 4, "controller_orientation": "right"},
            "right",
        ),
        SemanticObservation(
            {"source_color": 8, "controller_color": 4, "controller_orientation": "left"},
            "left",
        ),
        SemanticObservation(
            {"source_color": 8, "controller_color": 4, "controller_orientation": "left"},
            "left",
        ),
    ]
    model = learn_minimal_separator(observations)
    assert model is not None
    assert model.descriptor_names == ("controller_orientation",)
    assert model.predict({"controller_orientation": "right"}) == "right"
    assert model.causes_for("left") == (("left",),)


def test_backward_view_can_be_one_to_many_without_invalidating_forward_model():
    observations = [
        SemanticObservation({"cause": "A"}, 0),
        SemanticObservation({"cause": "B"}, 0),
        SemanticObservation({"cause": "C"}, 1),
    ]
    model = learn_minimal_separator(observations)
    assert model is not None
    assert model.descriptor_names == ("cause",)
    assert not model.backward_deterministic
    assert set(model.causes_for(0)) == {("A",), ("B",)}


def test_no_separator_under_arity_cap_when_effect_requires_two_bits():
    observations = [
        SemanticObservation({"a": a, "b": b}, a ^ b)
        for a, b in product((0, 1), repeat=2)
    ]
    assert learn_minimal_separator(observations, max_arity=1) is None
    model = learn_minimal_separator(observations, max_arity=2)
    assert model is not None
    assert model.descriptor_names == ("a", "b")
    assert separator_bcq_width(observations) == 2


def test_relative_completeness_decision_matches_bruteforce_small_descriptor_spaces():
    # For every Boolean effect table over two Boolean descriptors, verify that
    # the exact conflict-cover learner's arity<=2 existence decision agrees with
    # the obvious fact that the full pair (a,b) always determines a table.
    keys = list(product((0, 1), repeat=2))
    for effects in product((0, 1), repeat=4):
        observations = [
            SemanticObservation({"a": a, "b": b}, effect)
            for (a, b), effect in zip(keys, effects)
        ]
        assert separator_exists(observations, ("a", "b"), 2)


def _bruteforce_width(observations, names):
    effects = {observation.effect for observation in observations}
    if len(effects) < 2:
        return 1
    for arity in range(1, len(names) + 1):
        for subset in combinations(names, arity):
            table = {}
            deterministic = True
            for observation in observations:
                key = tuple(observation.descriptors[name] for name in subset)
                prior = table.get(key)
                if key in table and prior != observation.effect:
                    deterministic = False
                    break
                table[key] = observation.effect
            if deterministic:
                return arity
    return None


def test_conflict_cover_bcq_width_matches_exhaustive_search_for_every_three_bit_boolean_table():
    names = ("a", "b", "c")
    keys = list(product((0, 1), repeat=3))
    for effects in product((0, 1), repeat=len(keys)):
        observations = [
            SemanticObservation({"a": a, "b": b, "c": c}, effect)
            for (a, b, c), effect in zip(keys, effects)
        ]
        assert separator_bcq_width(observations, names) == _bruteforce_width(
            observations, names
        )


def test_unsupported_color_direction_key_stays_unknown():
    observations = [
        SemanticObservation({"color": 8}, "right"),
        SemanticObservation({"color": 6}, "up"),
    ]
    model = learn_minimal_separator(observations)
    assert model is not None
    assert model.predict({"color": 4}) is None
    assert model.predict({"color": 3}) is None
