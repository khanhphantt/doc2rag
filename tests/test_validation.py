from doc2rag.schema.canonical import CanonicalDocument, Exam, Section, SourceType, TestResult
from doc2rag.schema.intermediate import LocatedText, RawTable, RawTableRow
from doc2rag.validation.rules import validate_document


def _row(item_name: str, value: str) -> RawTableRow:
    return RawTableRow(item=LocatedText(id="item", text=item_name), value=LocatedText(id="value", text=value))


def _make_document(results: list[TestResult], exam_date: str | None = "2026-07-01") -> CanonicalDocument:
    return CanonicalDocument(
        document_id="doc-1",
        source_type=SourceType.IMAGE,
        exam=Exam(date=exam_date),
        sections=[Section(category="血液検査", results=results)],
    )


def test_value_matching_ocr_is_not_flagged():
    raw_tables = [RawTable(rows=[_row("BMI", "22.1")])]
    document = _make_document([TestResult(item="BMI", value="22.1")])

    validated = validate_document(document, raw_tables)

    assert validated.sections[0].results[0].needs_review is False


def test_value_mismatching_ocr_is_flagged():
    raw_tables = [RawTable(rows=[_row("BMI", "22.1")])]
    document = _make_document([TestResult(item="BMI", value="99.9")])

    validated = validate_document(document, raw_tables)

    assert validated.sections[0].results[0].needs_review is True
    assert any("value_mismatch" in flag for flag in validated.processing_meta.flags)


def test_implausible_value_is_flagged_even_if_matches_ocr():
    raw_tables = [RawTable(rows=[_row("身長", "999")])]
    document = _make_document([TestResult(item="身長", value="999")])

    validated = validate_document(document, raw_tables)

    assert validated.sections[0].results[0].needs_review is True
    assert any("implausible_value" in flag for flag in validated.processing_meta.flags)


def test_missing_value_is_flagged_generically():
    document = _make_document(
        [TestResult(item="白血球数", value=None), TestResult(item="尿糖定性", value="  ")]
    )

    validated = validate_document(document, raw_tables=[])

    assert all(r.needs_review for r in validated.sections[0].results)
    flags = validated.processing_meta.flags
    assert any("missing_value:血液検査:白血球数" in f for f in flags)
    assert any("missing_value:血液検査:尿糖定性" in f for f in flags)


def test_present_value_is_not_flagged_as_missing():
    document = _make_document([TestResult(item="BMI", value="22.1")])

    validated = validate_document(document, raw_tables=[])

    assert not any("missing_value" in f for f in validated.processing_meta.flags)


def test_missing_exam_date_is_flagged():
    document = _make_document([], exam_date=None)

    validated = validate_document(document, raw_tables=[])

    assert any("missing_required_field:exam.date" in flag for flag in validated.processing_meta.flags)
