from __future__ import annotations

from pathlib import Path

import openpyxl

from doc2rag.schema.intermediate import RawTable, RawTableRow

# Row layout assumption: item name / value / unit / reference range / judgement,
# in that column order. Real clinic exports vary; adjust per-facility mapping
# once sample files are available (see docs/ARCHITECTURE.md open items).
COLUMN_ORDER = ("item_name", "value", "unit", "reference_range", "judgement")


def load_excel_tables(path: Path) -> list[RawTable]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    tables: list[RawTable] = []

    for sheet in workbook.worksheets:
        rows: list[RawTableRow] = []
        for row in sheet.iter_rows(min_row=2, values_only=True):  # skip header row
            if not row or row[0] in (None, ""):
                continue
            values = dict(zip(COLUMN_ORDER, row))
            rows.append(
                RawTableRow(
                    item_name=str(values.get("item_name") or "").strip(),
                    value=_stringify(values.get("value")),
                    unit=_stringify(values.get("unit")),
                    reference_range=_stringify(values.get("reference_range")),
                    judgement=_stringify(values.get("judgement")),
                    confidence=1.0,
                )
            )
        if rows:
            tables.append(RawTable(rows=rows))

    return tables


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None
