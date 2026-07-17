"""Unit tests for the PaddleOCR-VL core that don't require the model weights."""

from __future__ import annotations

from types import SimpleNamespace

from doc2rag.vl import Block, Page, ParseOptions, ParseResult, build_interactive_html
from doc2rag.vl.parser import _markdown_text, _page_payload


def test_parse_options_defaults_match_demo():
    o = ParseOptions()
    kw = o.predict_kwargs()
    assert kw["use_layout_detection"] is True
    assert kw["use_seal_recognition"] is True
    assert kw["use_chart_recognition"] is False
    assert kw["layout_shape_mode"] == "auto"
    assert kw["prompt_label"] == "ocr"
    # by default all 7 auxiliary labels are filtered out
    assert set(kw["markdown_ignore_labels"]) == {
        "header", "header_image", "footer", "footer_image", "number", "footnote", "aside_text",
    }


def test_aux_toggle_removes_label_from_ignore():
    o = ParseOptions(parse_header=True, parse_footnote=True)
    ignore = o.ignore_labels()
    assert "header" not in ignore
    assert "footnote" not in ignore
    assert "footer" in ignore  # untouched labels stay filtered


def test_shape_and_prompt_pass_through():
    o = ParseOptions(layout_shape="poly", prompt_type="table", nms=False)
    kw = o.predict_kwargs()
    assert kw["layout_shape_mode"] == "poly"
    assert kw["prompt_label"] == "table"
    assert kw["layout_nms"] is False


def _sample_result() -> ParseResult:
    return ParseResult(
        markdown="# hi",
        pages=[
            Page(
                index=0, width=100, height=100, image="data:image/png;base64,AAAA",
                blocks=[
                    Block(id=0, order=2, label="text", content="hello <b>&", bbox=[0, 20, 50, 40]),
                    Block(id=1, order=1, label="table",
                          content="<table><tr><td>a</td></tr></table>", bbox=[0, 0, 50, 20]),
                ],
            )
        ],
    )


def test_build_interactive_html_links_and_renders():
    html = build_interactive_html(_sample_result())
    assert html.count('class="pp-box"') == 2
    assert html.count('class="pp-item"') == 2
    assert html.count("data-pp=") == 4  # 2 boxes + 2 list items
    assert 'data-pp="0-0"' in html and 'data-pp="0-1"' in html
    # table HTML is rendered as-is; plain text is escaped
    assert "<table>" in html
    assert "hello &lt;b&gt;&amp;" in html


def test_interactive_list_is_reading_order():
    html = build_interactive_html(_sample_result())
    # block id=1 has order 1 -> its list item comes before id=0 (order 2)
    assert html.index('class="pp-item" data-pp="0-1"') < html.index('class="pp-item" data-pp="0-0"')


def test_page_payload_unwraps_res_key():
    res = SimpleNamespace(json={"res": {"parsing_res_list": [], "width": 10, "height": 20}})
    payload = _page_payload(res)
    assert payload["width"] == 10 and payload["height"] == 20


def test_markdown_text_reads_markdown_texts():
    res = SimpleNamespace(markdown={"markdown_texts": "# Title\n\nbody"})
    assert _markdown_text(res) == "# Title\n\nbody"
    res_list = SimpleNamespace(markdown={"markdown_texts": ["a", "b"]})
    assert _markdown_text(res_list) == "a\n\nb"


def test_num_blocks():
    assert _sample_result().num_blocks == 2
