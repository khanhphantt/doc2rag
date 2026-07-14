from doc2rag.tables.html_grid import parse_table_html


def test_parses_simple_grid():
    html = "<table><tr><td>a</td><td>b</td></tr><tr><td>1</td><td>2</td></tr></table>"
    assert parse_table_html(html) == [["a", "b"], ["1", "2"]]


def test_colspan_expands_cell_across_columns():
    html = "<table><tr><td colspan='2'>merged</td></tr><tr><td>1</td><td>2</td></tr></table>"
    assert parse_table_html(html) == [["merged", "merged"], ["1", "2"]]


def test_ragged_rows_are_padded_to_rectangular():
    html = "<table><tr><td>a</td><td>b</td><td>c</td></tr><tr><td>1</td></tr></table>"
    assert parse_table_html(html) == [["a", "b", "c"], ["1", "", ""]]
