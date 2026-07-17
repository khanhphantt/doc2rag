from doc2rag.schema.intermediate import LocatedText
from doc2rag.tables.reconstruct import _match_header_roles, reconstruct_table_from_grid


def _grid(rows: list[list[str]]) -> list[list[LocatedText]]:
    return [[LocatedText(id=f"r{r}c{c}", text=text) for c, text in enumerate(row)] for r, row in enumerate(rows)]


def test_simple_header_table():
    grid = _grid(
        [
            ["項目", "結果", "単位", "基準値", "判定"],
            ["体重", "65.2", "kg", "-", "A"],
            ["BMI", "22.1", "", "18.5-25.0", "A"],
        ]
    )
    table = reconstruct_table_from_grid(grid)
    assert [row.item.text for row in table.rows] == ["体重", "BMI"]
    assert table.rows[0].value.text == "65.2"
    assert table.rows[0].unit.text == "kg"
    assert table.rows[1].reference_range.text == "18.5-25.0"


def test_repeating_column_group_header():
    grid = _grid(
        [
            ["項目", "結果", "単位", "基準値", "判定", "項目", "結果", "単位", "基準値", "判定"],
            ["身長", "170.5", "cm", "-", "A", "体重", "65.2", "kg", "-", "A"],
        ]
    )
    table = reconstruct_table_from_grid(grid)
    assert [row.item.text for row in table.rows] == ["身長", "体重"]
    assert table.rows[0].value.text == "170.5"
    assert table.rows[1].value.text == "65.2"


def test_no_recognizable_header_falls_back_to_first_two_cells():
    grid = _grid([["foo", "bar"], ["謎の項目", "123"]])
    table = reconstruct_table_from_grid(grid)
    assert len(table.rows) == 1
    assert table.rows[0].item.text == "謎の項目"
    assert table.rows[0].value.text == "123"


def test_empty_or_single_row_grid_yields_no_rows():
    assert reconstruct_table_from_grid([]).rows == []
    assert reconstruct_table_from_grid(_grid([["only header"]])).rows == []


def test_bare_stray_character_does_not_false_match_a_multichar_alias():
    # A lone "回" (common crop-bleed/OCR noise) perfectly substring-matches
    # the "今回" alias under partial_ratio; it must not be treated as a
    # real "value" header cell just for containing one of its characters.
    assert _match_header_roles(["回", "", ""]) == [None, None, None]


def test_noise_fragments_before_the_real_item_name_are_skipped_in_fallback():
    # Mirrors a real contaminated grid: a crop retry bled in a stray
    # grade-letter/digit column from a neighbouring table ahead of the
    # actual item name and value.
    grid = _grid([["回", "", ""], ["3", "尿糖定性", "(-)"]])
    table = reconstruct_table_from_grid(grid)
    assert len(table.rows) == 1
    assert table.rows[0].item.text == "尿糖定性"
    assert table.rows[0].value.text == "(-)"


def test_item_location_carries_through_to_the_reconstructed_row():
    grid = [
        [LocatedText(id="h0", text="項目"), LocatedText(id="h1", text="結果")],
        [
            LocatedText(id="d0", text="体重", location=None),
            LocatedText(id="d1", text="65.2"),
        ],
    ]
    table = reconstruct_table_from_grid(grid)
    assert table.rows[0].item.id == "d0"
