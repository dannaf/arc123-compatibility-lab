from arc123.observational_arc_grammar import (
    DEFAULT_OBSERVATIONAL_ARC_PRIMITIVES,
    DEFAULT_TERMINAL_RENDERERS,
    backward_equalize_segments,
    backward_render_background_column,
)
from arc123.observational_program_synthesis import compare_forward_only_to_forward_backward


def _grid(rows):
    return tuple(tuple(row) for row in rows)


def _component_count_fixture():
    # Foreground points are separated under both 4- and 8-connectivity.
    train_a = _grid(
        (
            (0, 0, 0, 0, 0),
            (0, 1, 0, 0, 0),
            (0, 0, 0, 0, 0),
            (0, 0, 0, 1, 0),
            (0, 0, 0, 0, 0),
        )
    )
    train_b = _grid(
        (
            (0, 0, 0, 0, 0, 0),
            (0, 1, 0, 0, 0, 0),
            (0, 0, 0, 1, 0, 0),
            (0, 0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0, 1),
        )
    )
    test = _grid(
        (
            (0, 0, 0),
            (0, 1, 0),
            (0, 0, 0),
        )
    )
    return (
        ((train_a, ((0,), (0,), (0,))), (train_b, ((0,), (0,), (0,), (0,)))),
        (test,),
    )


def _blank(h=10, w=16, bg=7):
    return [[bg for _ in range(w)] for _ in range(h)]


def _horizontal(lengths, target):
    grid = _blank()
    output = _blank()
    colors = (2, 4, 9, 1, 6)
    for index, (color, length) in enumerate(zip(colors, lengths)):
        row = 1 + index * 2
        for col in range(1, 1 + length):
            grid[row][col] = color
        for col in range(1, 1 + target):
            output[row][col] = color
    return tuple(map(tuple, grid)), tuple(map(tuple, output))


def test_background_column_backward_relation_is_exact_on_supported_and_rejects_wrong_shape():
    training, _ = _component_count_fixture()
    root, target = training[0]
    assert backward_render_background_column(root, target) == ((3,),)
    assert backward_render_background_column(root, ((0, 0),)) == ()


def test_forward_backward_prunes_dead_terminal_semantic_states_without_changing_exact_fiber():
    training, test_inputs = _component_count_fixture()
    result = compare_forward_only_to_forward_backward(
        training,
        test_inputs,
        DEFAULT_OBSERVATIONAL_ARC_PRIMITIVES,
        terminal_primitive_names=DEFAULT_TERMINAL_RENDERERS,
        max_cost=4,
    )
    fwd = result.forward_only
    fb = result.forward_backward

    assert fwd.exact_grid_states
    assert fb.exact_grid_states
    assert result.exact_prediction_equivalent
    assert fwd.exact_test_prediction_group_count == fb.exact_test_prediction_group_count == 1
    assert fb.backward_constraint_check_count > 0
    assert fb.backward_pruned_terminal_term_count > 0
    assert fb.quotient_state_count < fwd.quotient_state_count


def test_equalize_backward_relation_recovers_training_target_extent():
    root, target = _horizontal((2, 7, 12), 7)
    assert backward_equalize_segments(root, target) == ((7,),)


def test_forward_backward_pruning_preserves_e376_style_prediction_ambiguity():
    training = (
        _horizontal((2, 7, 12), 7),
        _horizontal((2, 4, 6), 4),
    )
    test_input, target_4 = _horizontal((1, 3, 4, 5, 7), 4)
    _, target_5 = _horizontal((1, 3, 4, 5, 7), 5)

    result = compare_forward_only_to_forward_backward(
        training,
        (test_input,),
        DEFAULT_OBSERVATIONAL_ARC_PRIMITIVES,
        terminal_primitive_names=DEFAULT_TERMINAL_RENDERERS,
        max_cost=6,
    )
    fwd = result.forward_only
    fb = result.forward_backward

    assert result.exact_prediction_equivalent
    assert fwd.exact_test_prediction_group_count == 2
    assert fb.exact_test_prediction_group_count == 2
    assert not fwd.has_prediction_singularity
    assert not fb.has_prediction_singularity

    train_count = len(training)
    fwd_test_predictions = {state.values[train_count] for state in fwd.exact_grid_states}
    fb_test_predictions = {state.values[train_count] for state in fb.exact_grid_states}
    assert fwd_test_predictions == fb_test_predictions == {target_4, target_5}
    assert fb.backward_pruned_terminal_term_count > 0
