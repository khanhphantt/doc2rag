from __future__ import annotations

from rapidfuzz import fuzz, process

from doc2rag.schema.intermediate import RawTable, RawTableRow
from doc2rag.tables.html_grid import parse_table_html
from doc2rag.tables.item_dictionary import normalize_item_name

# Maps a role to the header labels PP-Structure/OCR commonly emits for it.
# Header cells are fuzzy-matched against these to locate columns instead of
# assuming a fixed column order, since clinics lay tables out differently.
_HEADER_ALIASES: dict[str, list[str]] = {
    "item_name": ["項目", "検査項目", "種目", "検査名"],
    "value": ["結果", "測定値", "値", "検査結果"],
    "unit": ["単位"],
    "reference_range": ["基準値", "正常値", "基準範囲"],
    "judgement": ["判定", "結果判定", "区分"],
}

_HEADER_MATCH_THRESHOLD = 70


def reconstruct_table(table_html: str, page: int = 0) -> RawTable:
    """Convert PP-Structure table HTML into normalized (item, value, ...) rows.

    Health-checkup tables commonly repeat the same (item/value/unit/...)
    column group 2-3 times per physical row to save vertical space, so this
    detects the header column-role pattern once and re-applies it to every
    repeated group found in the row, rather than assuming a single flat
    row-per-item table.
    """
    grid = parse_table_html(table_html)
    if len(grid) < 2:
        return RawTable(rows=[], page=page)

    header, *data_rows = grid
    column_roles = _match_header_roles(header)
    group_size = len(_HEADER_ALIASES) if _is_repeating_header(header, column_roles) else len(header)

    rows: list[RawTableRow] = []
    for data_row in data_rows:
        for group_start in range(0, len(data_row), group_size):
            group = data_row[group_start : group_start + group_size]
            group_roles = column_roles[group_start : group_start + group_size]
            row = _row_from_group(group, group_roles)
            if row is not None:
                rows.append(row)

    return RawTable(rows=rows, page=page)


def _match_header_roles(header: list[str]) -> list[str | None]:
    roles: list[str | None] = []
    for cell in header:
        role = _best_role_for_cell(cell)
        roles.append(role)
    return roles


def _best_role_for_cell(cell: str) -> str | None:
    best_role: str | None = None
    best_score = 0.0
    for role, aliases in _HEADER_ALIASES.items():
        match = process.extractOne(cell, aliases, scorer=fuzz.ratio, score_cutoff=_HEADER_MATCH_THRESHOLD)
        if match and match[1] > best_score:
            best_role, best_score = role, match[1]
    return best_role


def _is_repeating_header(header: list[str], roles: list[str | None]) -> bool:
    matched = sum(1 for r in roles if r is not None)
    return matched >= 2 and len(header) > len(_HEADER_ALIASES)


def _row_from_group(group: list[str], roles: list[str | None]) -> RawTableRow | None:
    values: dict[str, str] = {}
    for cell, role in zip(group, roles):
        if role and cell:
            values.setdefault(role, cell)

    # Fallback for tables with no recognizable header: assume the first
    # non-empty cell is the item name and the second is the value.
    if "item_name" not in values:
        non_empty = [c for c in group if c]
        if len(non_empty) < 2:
            return None
        values.setdefault("item_name", non_empty[0])
        values.setdefault("value", non_empty[1])

    if not values.get("item_name"):
        return None

    canonical_name, match_score = normalize_item_name(values["item_name"])
    return RawTableRow(
        item_name=canonical_name,
        value=values.get("value") or None,
        unit=values.get("unit") or None,
        reference_range=values.get("reference_range") or None,
        judgement=values.get("judgement") or None,
        confidence=match_score if match_score > 0 else 0.5,
    )
