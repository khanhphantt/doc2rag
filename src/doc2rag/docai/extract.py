from __future__ import annotations

from dataclasses import dataclass, field

from google.cloud import documentai_v1 as documentai

from doc2rag.schema.canonical import PageMeta
from doc2rag.schema.intermediate import Location, LocatedText, NormalizedVertex


@dataclass
class ExtractedDocument:
    pages: list[PageMeta] = field(default_factory=list)
    table_grids: list[tuple[int, list[list[LocatedText]]]] = field(default_factory=list)
    """(page_index, grid) pairs - grid[0] is the header row when Document AI
    identified one (table.header_rows), else the first body row, matching
    the row-per-list-item shape reconstruct_table_from_grid expects."""
    paragraphs: list[LocatedText] = field(default_factory=list)


def extract_document(document: documentai.Document) -> ExtractedDocument:
    pages = [
        PageMeta(page_number=page.page_number, width=page.dimension.width, height=page.dimension.height)
        for page in document.pages
    ]

    table_grids: list[tuple[int, list[list[LocatedText]]]] = []
    paragraphs: list[LocatedText] = []

    for page_index, page in enumerate(document.pages):
        for table_index, table in enumerate(page.tables):
            grid = _table_grid(document.text, page_index, table_index, table)
            if grid:
                table_grids.append((page_index, grid))

        for para_index, paragraph in enumerate(page.paragraphs):
            text = _text_from_layout(document.text, paragraph.layout)
            if not text:
                continue
            paragraphs.append(
                LocatedText(
                    id=f"page{page_index}_para{para_index}",
                    text=text,
                    location=_location_from_layout(paragraph.layout, page_index),
                )
            )

    return ExtractedDocument(pages=pages, table_grids=table_grids, paragraphs=paragraphs)


def _table_grid(
    full_text: str, page_index: int, table_index: int, table: documentai.Document.Page.Table
) -> list[list[LocatedText]]:
    grid: list[list[LocatedText]] = []
    for row_index, row in enumerate([*table.header_rows, *table.body_rows]):
        cells = [
            LocatedText(
                id=f"table{table_index}_row{row_index}_col{col_index}",
                text=_text_from_layout(full_text, cell.layout),
                location=_location_from_layout(cell.layout, page_index),
            )
            for col_index, cell in enumerate(row.cells)
        ]
        grid.append(cells)
    return grid


def _text_from_layout(full_text: str, layout: documentai.Document.Page.Layout) -> str:
    segments = layout.text_anchor.text_segments
    if not segments:
        return ""
    parts = [full_text[int(segment.start_index or 0) : int(segment.end_index)] for segment in segments]
    return "".join(parts).strip()


def _location_from_layout(layout: documentai.Document.Page.Layout, page_index: int) -> Location | None:
    vertices = layout.bounding_poly.normalized_vertices
    if not vertices:
        return None
    return Location(page=page_index, vertices=[NormalizedVertex(x=v.x, y=v.y) for v in vertices])
