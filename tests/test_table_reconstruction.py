from doc2rag.tables.reconstruct import reconstruct_table


def test_simple_header_table():
    html = """
    <table>
      <tr><td>項目</td><td>結果</td><td>単位</td><td>基準値</td><td>判定</td></tr>
      <tr><td>体重</td><td>65.2</td><td>kg</td><td>-</td><td>A</td></tr>
      <tr><td>BMI</td><td>22.1</td><td></td><td>18.5-25.0</td><td>A</td></tr>
    </table>
    """
    table = reconstruct_table(html)
    assert [row.item_name for row in table.rows] == ["体重", "BMI"]
    assert table.rows[0].value == "65.2"
    assert table.rows[0].unit == "kg"
    assert table.rows[1].reference_range == "18.5-25.0"


def test_repeating_column_group_header():
    html = """
    <table>
      <tr>
        <td>項目</td><td>結果</td><td>単位</td><td>基準値</td><td>判定</td>
        <td>項目</td><td>結果</td><td>単位</td><td>基準値</td><td>判定</td>
      </tr>
      <tr>
        <td>身長</td><td>170.5</td><td>cm</td><td>-</td><td>A</td>
        <td>体重</td><td>65.2</td><td>kg</td><td>-</td><td>A</td>
      </tr>
    </table>
    """
    table = reconstruct_table(html)
    assert [row.item_name for row in table.rows] == ["身長", "体重"]
    assert table.rows[0].value == "170.5"
    assert table.rows[1].value == "65.2"


def test_no_recognizable_header_falls_back_to_first_two_cells():
    html = """
    <table>
      <tr><td>foo</td><td>bar</td></tr>
      <tr><td>謎の項目</td><td>123</td></tr>
    </table>
    """
    table = reconstruct_table(html)
    assert len(table.rows) == 1
    assert table.rows[0].item_name == "謎の項目"
    assert table.rows[0].value == "123"


def test_empty_or_single_row_table_yields_no_rows():
    assert reconstruct_table("<table></table>").rows == []
    assert reconstruct_table("<table><tr><td>only header</td></tr></table>").rows == []
