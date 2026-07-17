from __future__ import annotations

from doc2rag.schema.canonical import CanonicalDocument
from doc2rag.schema.intermediate import Location, RawTable


def resolve_locations(document: CanonicalDocument, structured: dict, raw_tables: list[RawTable]) -> CanonicalDocument:
    """Attach each TestResult's location from the source_row_id the LLM
    echoed back in `structured` (the raw LLM output dict - TestResult itself
    has no source_row_id field, so this must run before that field is
    dropped), resolved against the raw table rows indexed *before* the LLM
    ever ran. The LLM never sees or produces geometry itself, since it
    cannot be trusted to reproduce coordinates verbatim.

    A source_row_id that doesn't exist in the index is flagged as a likely
    hallucination; the result's location is left None rather than guessed.
    """
    location_by_id = _index_locations(raw_tables)

    for section, structured_section in zip(document.sections, structured["sections"]):
        for result, structured_result in zip(section.results, structured_section["results"]):
            source_row_id = structured_result.get("source_row_id")
            if source_row_id is None:
                continue
            location = location_by_id.get(source_row_id)
            if location is None:
                document.processing_meta.flags.append(
                    f"unknown_source_row_id:{section.category}:{result.item}:{source_row_id}"
                )
                continue
            result.location = location

    return document


def _index_locations(raw_tables: list[RawTable]) -> dict[str, Location]:
    index: dict[str, Location] = {}
    for table in raw_tables:
        for row in table.rows:
            if row.item.location is not None:
                index[row.item.id] = row.item.location
    return index
