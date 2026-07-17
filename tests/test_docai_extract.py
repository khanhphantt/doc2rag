import pytest
from google.cloud import documentai_v1 as documentai

from doc2rag.docai.extract import extract_document


def _layout(start: int, end: int, x: float = 0.0, y: float = 0.0) -> documentai.Document.Page.Layout:
    return documentai.Document.Page.Layout(
        text_anchor=documentai.Document.TextAnchor(
            text_segments=[documentai.Document.TextAnchor.TextSegment(start_index=start, end_index=end)]
        ),
        bounding_poly=documentai.BoundingPoly(normalized_vertices=[documentai.NormalizedVertex(x=x, y=y)]),
    )


def _fixture_document() -> documentai.Document:
    text = "項目結果体重65.2所見:良好"
    #        0  1  2 3    4 56789...
    table = documentai.Document.Page.Table(
        header_rows=[
            documentai.Document.Page.Table.TableRow(
                cells=[
                    documentai.Document.Page.Table.TableCell(layout=_layout(0, 2, x=0.1, y=0.1)),
                    documentai.Document.Page.Table.TableCell(layout=_layout(2, 4, x=0.3, y=0.1)),
                ]
            )
        ],
        body_rows=[
            documentai.Document.Page.Table.TableRow(
                cells=[
                    documentai.Document.Page.Table.TableCell(layout=_layout(4, 6, x=0.1, y=0.2)),
                    documentai.Document.Page.Table.TableCell(layout=_layout(6, 10, x=0.3, y=0.2)),
                ]
            )
        ],
    )
    paragraph = documentai.Document.Page.Paragraph(layout=_layout(10, len(text), x=0.1, y=0.5))
    page = documentai.Document.Page(
        page_number=1,
        dimension=documentai.Document.Page.Dimension(width=800, height=600),
        tables=[table],
        paragraphs=[paragraph],
    )
    return documentai.Document(text=text, pages=[page])


def test_extracts_page_meta():
    extracted = extract_document(_fixture_document())
    assert len(extracted.pages) == 1
    assert extracted.pages[0].page_number == 1
    assert extracted.pages[0].width == 800
    assert extracted.pages[0].height == 600


def test_extracts_table_grid_with_header_and_body_rows_and_location():
    extracted = extract_document(_fixture_document())
    assert len(extracted.table_grids) == 1
    page_index, grid = extracted.table_grids[0]
    assert page_index == 0
    assert [cell.text for cell in grid[0]] == ["項目", "結果"]
    assert [cell.text for cell in grid[1]] == ["体重", "65.2"]
    assert grid[1][0].location.page == 0
    assert grid[1][0].location.vertices[0].x == pytest.approx(0.1)


def test_extracts_paragraphs():
    extracted = extract_document(_fixture_document())
    assert len(extracted.paragraphs) == 1
    assert extracted.paragraphs[0].text == "所見:良好"


def test_skips_empty_paragraphs():
    text = "AB"
    page = documentai.Document.Page(
        page_number=1,
        dimension=documentai.Document.Page.Dimension(width=100, height=100),
        paragraphs=[documentai.Document.Page.Paragraph(layout=_layout(0, 0))],
    )
    extracted = extract_document(documentai.Document(text=text, pages=[page]))
    assert extracted.paragraphs == []
