from __future__ import annotations

import uuid
from pathlib import Path

from doc2rag.config import Settings, get_settings
from doc2rag.docai import DocAiClient, extract_document
from doc2rag.ingestion.excel import load_excel_tables
from doc2rag.ingestion.loaders import detect_source_type, mime_type_for
from doc2rag.schema.canonical import (
    CanonicalDocument,
    Exam,
    PageMeta,
    Patient,
    ProcessingMeta,
    Section,
    SourceType,
    TestResult,
)
from doc2rag.schema.intermediate import LocatedText, RawTable
from doc2rag.structuring import get_structuring_client
from doc2rag.structuring.location_resolver import resolve_locations
from doc2rag.tables import reconstruct_table_from_grid
from doc2rag.validation import validate_document


class DocumentPipeline:
    """Wires ingestion -> Document AI extraction -> table reconstruction ->
    LLM structuring -> validation/location resolution into a single call,
    per the pipeline design in docs/ARCHITECTURE.md.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._docai_client = DocAiClient(self._settings)
        self._structuring_client = get_structuring_client(self._settings)

    def process(self, path: Path) -> CanonicalDocument:
        source_type = detect_source_type(path)
        document_id = str(uuid.uuid4())

        if source_type == SourceType.EXCEL:
            raw_tables = load_excel_tables(path)
            text_regions: list[LocatedText] = []
            pages: list[PageMeta] = []
        else:
            raw_tables, text_regions, pages = self._process_scanned_document(path)

        structured = self._structuring_client.structure(text_regions, raw_tables)
        document = _to_canonical_document(
            document_id, source_type, structured, self._structuring_client.model_name, pages
        )
        document = validate_document(document, raw_tables)
        document = resolve_locations(document, structured, raw_tables)
        return document

    def _process_scanned_document(
        self, path: Path
    ) -> tuple[list[RawTable], list[LocatedText], list[PageMeta]]:
        content = path.read_bytes()
        docai_document = self._docai_client.process(content, mime_type_for(path))
        extracted = extract_document(docai_document)

        raw_tables = [
            reconstruct_table_from_grid(grid, page=page_index) for page_index, grid in extracted.table_grids
        ]
        return raw_tables, extracted.paragraphs, extracted.pages


def _to_canonical_document(
    document_id: str, source_type: SourceType, structured: dict, llm_model: str, pages: list[PageMeta]
) -> CanonicalDocument:
    sections = [
        Section(
            category=section["category"],
            free_text=section["free_text"],
            results=[TestResult(**result) for result in section["results"]],
        )
        for section in structured["sections"]
    ]
    return CanonicalDocument(
        document_id=document_id,
        source_type=source_type,
        patient=Patient(**structured["patient"]),
        exam=Exam(**structured["exam"]),
        sections=sections,
        overall_judgement=structured["overall_judgement"],
        doctor_comment=structured["doctor_comment"],
        pages=pages,
        processing_meta=ProcessingMeta(llm_model=llm_model),
    )


def get_pipeline() -> DocumentPipeline:
    return DocumentPipeline(get_settings())
