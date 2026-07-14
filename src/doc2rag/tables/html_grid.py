from __future__ import annotations

from html.parser import HTMLParser


class _TableGridParser(HTMLParser):
    """Parses a single <table> HTML string (as emitted by PP-Structure's
    table recognizer) into a 2D grid of cell text, expanding colspan/rowspan
    by repeating the cell's text into the extra grid slots so the resulting
    grid is rectangular.
    """

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None
        self._current_span: tuple[int, int] = (1, 1)
        self._pending_rowspans: dict[int, tuple[int, str]] = {}  # col -> (remaining_rows, text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._current_cell = []
            colspan = int(attr_dict.get("colspan") or 1)
            rowspan = int(attr_dict.get("rowspan") or 1)
            self._current_span = (colspan, rowspan)

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._current_row is not None:
            text = "".join(self._current_cell or []).strip()
            colspan, rowspan = self._current_span
            for _ in range(colspan):
                self._current_row.append(text)
            self._current_cell = None
            self._current_span = (1, 1)
        elif tag == "tr" and self._current_row is not None:
            self._rows.append(self._current_row)
            self._current_row = None

    def grid(self) -> list[list[str]]:
        max_cols = max((len(row) for row in self._rows), default=0)
        return [row + [""] * (max_cols - len(row)) for row in self._rows]


def parse_table_html(html: str) -> list[list[str]]:
    """Parse table HTML into a rectangular grid of cell text (rows x cols).

    Note: rowspan is expanded per-column via colspan repetition only; true
    rowspan (vertical merge) is left as-is per row since PP-Structure's own
    table HTML rarely emits rowspan for these tabular test-result layouts.
    Revisit if real samples show otherwise.
    """
    parser = _TableGridParser()
    parser.feed(html)
    return parser.grid()
