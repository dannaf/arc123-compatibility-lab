from itertools import product

from arc123.callosal_separator import (
    SemanticObservation,
    learn_minimal_separator,
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


def test_relative_completeness_decision_matches_bruteforce_small_descriptor_spaces():
    # For every Boolean effect table over two Boolean descriptors, verify that
    # the exhaustive learner's arity<=2 existence decision agrees with the
    # obvious fact that the full pair (a,b) always determines a table.
    keys = list(product((0, 1), repeat=2))
    for effects in product((0, 1), repeat=4):
        observations = [
            SemanticObservation({"a": a, "b": b}, effect)
            for (a, b), effect in zip(keys, effects)
        ]
        assert separator_exists(observations, ("a", "b"), 2)


def test_unsupported_color_direction_key_stays_unknown():
    observations = [
        SemanticObservation({"color": 8}, "right"),
        SemanticObservation({"color": 6}, "up"),
    ]
    model = learn_minimal_separator(observations)
    assert model is not None
    assert model.predict({"color": 4}) is None
    assert model.predict({"color": 3}) is None
