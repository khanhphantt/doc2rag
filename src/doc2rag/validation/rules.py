from __future__ import annotations

from doc2rag.schema.canonical import CanonicalDocument
from doc2rag.schema.intermediate import RawTable, RawTableRow

# Loose plausibility bounds (min, max) per canonical item name, used only to
# catch obviously-wrong OCR/LLM values (e.g. a decimal point dropped), not to
# do any clinical judgement. Extend as new item types are handled.
PLAUSIBILITY_RANGES: dict[str, tuple[float, float]] = {
    "身長": (100.0, 220.0),
    "体重": (25.0, 250.0),
    "BMI": (10.0, 60.0),
    "腹囲": (40.0, 200.0),
    "収縮期血圧": (60.0, 260.0),
    "拡張期血圧": (30.0, 160.0),
    "空腹時血糖": (30.0, 600.0),
    "HbA1c": (3.0, 20.0),
}

REQUIRED_EXAM_FIELDS = ("date",)


def validate_document(document: CanonicalDocument, raw_tables: list[RawTable]) -> CanonicalDocument:
    """Cross-check the LLM-structured document against OCR ground truth and
    flag implausible/mismatched fields with needs_review=True in place.

    This never silently corrects a value — it only raises flags for a human
    reviewer, since silently "fixing" a health value is worse than leaving it
    marked uncertain.
    """
    raw_by_item = _index_raw_rows(raw_tables)

    for section in document.sections:
        for result in section.results:
            if _missing_value(result.value):
                result.needs_review = True
                document.processing_meta.flags.append(f"missing_value:{section.category}:{result.item}")
            if _mismatches_ocr(result.item, result.value, raw_by_item):
                result.needs_review = True
                document.processing_meta.flags.append(f"value_mismatch:{section.category}:{result.item}")
            if _out_of_plausible_range(result.item, result.value):
                result.needs_review = True
                document.processing_meta.flags.append(f"implausible_value:{section.category}:{result.item}")

    for field in REQUIRED_EXAM_FIELDS:
        if not getattr(document.exam, field):
            document.processing_meta.flags.append(f"missing_required_field:exam.{field}")

    return document


def _index_raw_rows(raw_tables: list[RawTable]) -> dict[str, list[RawTableRow]]:
    index: dict[str, list[RawTableRow]] = {}
    for table in raw_tables:
        for row in table.rows:
            index.setdefault(row.item.text, []).append(row)
    return index


def _missing_value(value: str | None) -> bool:
    """Flag any result the LLM produced without a value. In a 健康診断 table
    every item row carries a current (今回) result, so a missing value means
    the value was present in OCR but not extracted (e.g. from a cell whose
    OCR text was too garbled for the LLM to read confidently) — a human
    should reconcile it. Generic across all sections/tables, not tied to any
    specific item.
    """
    return value is None or not value.strip()


def _mismatches_ocr(item: str, value: str | None, raw_by_item: dict[str, list[RawTableRow]]) -> bool:
    candidates = raw_by_item.get(item)
    if not candidates or value is None:
        return False
    return not any(row.value and row.value.text == value for row in candidates)


def _out_of_plausible_range(item: str, value: str | None) -> bool:
    bounds = PLAUSIBILITY_RANGES.get(item)
    if bounds is None or value is None:
        return False
    try:
        numeric_value = float(value)
    except ValueError:
        return False
    low, high = bounds
    return not (low <= numeric_value <= high)
