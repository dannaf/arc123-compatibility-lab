from arc123.observational_arc_grammar import DEFAULT_OBSERVATIONAL_ARC_PRIMITIVES
from arc123.observational_program_synthesis import synthesize_observational_quotient


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


def test_nary_synthesis_preserves_parameter_prediction_ambiguity():
    # Both second-longest and ceil((min+max)/2) equal 7 and 4 on training.
    training = (
        _horizontal((2, 7, 12), 7),
        _horizontal((2, 4, 6), 4),
    )
    # On the current test input they diverge: second-longest=5, midrange=4.
    test_input, _ = _horizontal((1, 3, 4, 5, 7), 4)
    result = synthesize_observational_quotient(
        training,
        (test_input,),
        DEFAULT_OBSERVATIONAL_ARC_PRIMITIVES,
        max_cost=6,
    )
    names = {state.term.name for state in result.exact_grid_states}
    assert any("sequence_second_desc" in name for name in names)
    assert any("sequence_min" in name and "sequence_max" in name and "add_ints" in name for name in names)
    assert result.exact_test_prediction_group_count == 2
    assert not result.has_prediction_singularity
