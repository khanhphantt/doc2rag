from doc2rag.schema.canonical import CanonicalDocument, Section, SourceType, TestResult
from doc2rag.schema.intermediate import Location, LocatedText, NormalizedVertex, RawTable, RawTableRow
from doc2rag.structuring.location_resolver import resolve_locations

_LOCATION = Location(page=0, vertices=[NormalizedVertex(x=0.1, y=0.2)])


def _document(results: list[TestResult]) -> CanonicalDocument:
    return CanonicalDocument(
        document_id="doc-1",
        source_type=SourceType.IMAGE,
        sections=[Section(category="測定", results=results)],
    )


def _raw_tables() -> list[RawTable]:
    row = RawTableRow(item=LocatedText(id="row-1", text="体重", location=_LOCATION))
    return [RawTable(rows=[row])]


def test_valid_source_row_id_attaches_location():
    document = _document([TestResult(item="体重", value="65.2")])
    structured = {"sections": [{"results": [{"source_row_id": "row-1"}]}]}

    resolved = resolve_locations(document, structured, _raw_tables())

    assert resolved.sections[0].results[0].location == _LOCATION
    assert resolved.processing_meta.flags == []


def test_unknown_source_row_id_is_flagged_and_location_stays_none():
    document = _document([TestResult(item="体重", value="65.2")])
    structured = {"sections": [{"results": [{"source_row_id": "does-not-exist"}]}]}

    resolved = resolve_locations(document, structured, _raw_tables())

    assert resolved.sections[0].results[0].location is None
    assert resolved.processing_meta.flags == ["unknown_source_row_id:測定:体重:does-not-exist"]


def test_null_source_row_id_leaves_location_none_without_flagging():
    document = _document([TestResult(item="所見", value=None)])
    structured = {"sections": [{"results": [{"source_row_id": None}]}]}

    resolved = resolve_locations(document, structured, _raw_tables())

    assert resolved.sections[0].results[0].location is None
    assert resolved.processing_meta.flags == []
