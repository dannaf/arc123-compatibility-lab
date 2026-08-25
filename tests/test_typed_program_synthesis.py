from arc123.typed_program_synthesis import (
    enumerate_typed_programs,
    synthesize_exact_program_fiber,
)


def _g(rows):
    return tuple(tuple(row) for row in rows)


def test_enumerator_builds_type_correct_compositions_not_named_rules():
    names = {program.name for program in enumerate_typed_programs(max_steps=4, max_cost=4)}
    assert "synth[components4 -> count -> add1 -> render_background_column]" in names
    assert "synth[components4 -> select_unique_min_area -> crop_bbox]" in names
    assert not any("component_count_plus_one_blank_column" in name for name in names)
    assert not any("component_select_extract" in name for name in names)


def test_synthesizes_component_count_measure_render_pipeline():
    train = (
        (
            _g([
                [0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 2, 0],
                [0, 1, 0, 0, 0, 0],
                [0, 0, 0, 3, 3, 0],
                [0, 0, 0, 0, 0, 0],
            ]),
            _g([[0], [0], [0], [0]]),
        ),
        (
            _g([
                [0, 0, 0, 0, 0],
                [0, 4, 4, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 5, 0, 0],
                [0, 0, 5, 0, 0],
            ]),
            _g([[0], [0], [0]]),
        ),
    )
    result = synthesize_exact_program_fiber(train, max_steps=4, max_cost=4)
    names = {program.name for program in result.programs}
    assert result.minimum_exact_cost == 4
    assert "synth[components4 -> count -> add1 -> render_background_column]" in names
    assert result.exact_program_count >= 1
    for program in result.programs:
        assert all(program.predict(inp) == out for inp, out in train)


def test_synthesizes_object_select_measure_extract_pipeline():
    train = (
        (
            _g([
                [0, 0, 0, 0, 0, 0, 0],
                [0, 2, 2, 0, 7, 7, 7],
                [0, 0, 0, 0, 7, 7, 7],
                [0, 0, 0, 0, 0, 0, 0],
            ]),
            _g([[2, 2]]),
        ),
        (
            _g([
                [0, 0, 0, 0, 0, 0],
                [0, 3, 0, 8, 8, 8],
                [0, 3, 3, 8, 8, 8],
                [0, 0, 0, 8, 8, 8],
                [0, 0, 0, 0, 0, 0],
            ]),
            _g([[3, 0], [3, 3]]),
        ),
    )
    result = synthesize_exact_program_fiber(train, max_steps=3, max_cost=3)
    names = {program.name for program in result.programs}
    assert result.minimum_exact_cost == 3
    assert "synth[components4 -> select_unique_min_area -> crop_bbox]" in names
    for program in result.programs:
        assert all(program.predict(inp) == out for inp, out in train)


def test_synthesis_uses_all_demonstrations_not_first_demo_only():
    # On demo 1, both min-area and max-area selection happen to emit the same
    # one-cell crop shape/color. Demo 2 disambiguates the correct semantic rule.
    train = (
        (
            _g([
                [0, 0, 0, 0, 0],
                [0, 4, 0, 4, 4],
                [0, 0, 0, 0, 0],
            ]),
            _g([[4]]),
        ),
        (
            _g([
                [0, 0, 0, 0, 0, 0],
                [0, 5, 0, 9, 9, 9],
                [0, 5, 0, 9, 9, 9],
                [0, 0, 0, 9, 9, 9],
                [0, 0, 0, 0, 0, 0],
            ]),
            _g([[5], [5]]),
        ),
    )
    result = synthesize_exact_program_fiber(train, max_steps=3, max_cost=3)
    names = {program.name for program in result.programs}
    assert "synth[components4 -> select_unique_min_area -> crop_bbox]" in names
    assert "synth[components4 -> select_unique_max_area -> crop_bbox]" not in names
