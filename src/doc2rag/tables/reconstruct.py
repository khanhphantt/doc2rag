from __future__ import annotations

from rapidfuzz import fuzz

from doc2rag.schema.intermediate import LocatedText, RawTable, RawTableRow
from doc2rag.tables.item_dictionary import normalize_item_name

# Maps a role to the header labels Document AI's OCR commonly emits for it.
# Header cells are fuzzy-matched against these to locate columns instead of
# assuming a fixed column order, since clinics lay tables out differently.
_HEADER_ALIASES: dict[str, list[str]] = {
    "item_name": ["項目", "検査項目", "種目", "検査名"],
    "value": ["結果", "測定値", "値", "検査結果", "今回"],
    "unit": ["単位"],
    "reference_range": ["基準値", "正常値", "基準範囲"],
    "judgement": ["判定", "結果判定", "区分"],
}

_HEADER_MATCH_THRESHOLD = 70


def reconstruct_table_from_grid(grid: list[list[LocatedText]], page: int = 0) -> RawTable:
    """Convert a Document AI table grid into normalized (item, value, ...) rows.

    Health-checkup tables commonly repeat the same (item/value/unit/...)
    column group 2-3 times per physical row to save vertical space, so this
    detects the header column-role pattern once and re-applies it to every
    repeated group found in the row, rather than assuming a single flat
    row-per-item table. `grid[0]` is Document AI's header row when it
    identified one, else the first body row.
    """
    if len(grid) < 2:
        return RawTable(rows=[], page=page)

    header, *data_rows = grid
    header_texts = [cell.text for cell in header]
    column_roles = _match_header_roles(header_texts)
    group_size = len(_HEADER_ALIASES) if _is_repeating_header(header_texts, column_roles) else len(header)

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
    return [_best_role_for_cell(cell) for cell in header]


def _best_role_for_cell(cell: str) -> str | None:
    # OCR frequently inserts stray spaces inside header text (e.g. "今 回"
    # for "今回", "検 査 項 目" for "検査項目"); strip whitespace before
    # matching so those still line up with the (space-free) aliases.
    normalized = cell.replace(" ", "").replace("　", "")
    if not normalized:
        return None

    best_role: str | None = None
    best_score = 0.0
    for role, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            # ratio catches near-exact matches; partial_ratio catches an
            # alias appearing as a substring of a longer header label (e.g.
            # "機能別項目" for the "項目" family), which plain ratio
            # penalizes for the extra characters. Gated on the alias AND the
            # cell both being 2+ characters: a lone stray character (common
            # OCR/crop-bleed noise) would otherwise "contain" almost any
            # alias trivially — e.g. a bare "回" perfectly substring-matches
            # "今回" and gets misread as a real header cell.
            score = fuzz.ratio(normalized, alias)
            if len(alias) >= 2 and len(normalized) >= 2:
                score = max(score, fuzz.partial_ratio(normalized, alias))
            if score >= _HEADER_MATCH_THRESHOLD and score > best_score:
                best_role, best_score = role, score
    return best_role


def _looks_like_item_name(cell: str) -> bool:
    """Filter for the ambiguous "no recognizable header" fallback below:
    real 健康診断 item names are multi-character Japanese terms, whereas
    contamination from a neighbouring table/crop (grade letters like "A"/
    "D1", bare list-numbering digits) tends to be short and script-free.
    Prevents that noise from being mistaken for the item name just because
    it happens to be the first non-empty cell in an otherwise unlabeled row.
    """
    return len(cell) >= 2 and any(0x3040 <= ord(ch) <= 0x9FFF for ch in cell)


def _is_repeating_header(header: list[str], roles: list[str | None]) -> bool:
    matched = sum(1 for r in roles if r is not None)
    return matched >= 2 and len(header) > len(_HEADER_ALIASES)


def _row_from_group(group: list[LocatedText], roles: list[str | None]) -> RawTableRow | None:
    values: dict[str, LocatedText] = {}
    assigned_indices: set[int] = set()
    for idx, (cell, role) in enumerate(zip(group, roles)):
        if role and cell.text:
            values.setdefault(role, cell)
            assigned_indices.add(idx)

    # Fallback for tables with no recognizable header: assume the first
    # plausible-looking item name is the item, and the value is whatever
    # comes after it (not just "the next non-empty cell from the start" —
    # noise columns preceding the real item name, e.g. bled in from a
    # neighbouring table during a crop retry, would otherwise get picked
    # as the item name and push the real value out of position).
    if "item_name" not in values:
        candidates = [(idx, c) for idx, c in enumerate(group) if c.text and idx not in assigned_indices]
        item_candidates = [(idx, c) for idx, c in candidates if _looks_like_item_name(c.text)]
        if not item_candidates:
            return None
        item_idx, item_cell = item_candidates[0]
        values.setdefault("item_name", item_cell)
        value_candidates = [c for idx, c in candidates if idx > item_idx]
        if value_candidates:
            values.setdefault("value", value_candidates[0])

    item_cell = values.get("item_name")
    if item_cell is None or not item_cell.text:
        return None

    canonical_name, match_score = normalize_item_name(item_cell.text)
    item_located = LocatedText(id=item_cell.id, text=canonical_name, location=item_cell.location)
    return RawTableRow(
        item=item_located,
        value=values.get("value"),
        unit=values.get("unit"),
        reference_range=values.get("reference_range"),
        judgement=values.get("judgement"),
        confidence=match_score if match_score > 0 else 0.5,
    )
