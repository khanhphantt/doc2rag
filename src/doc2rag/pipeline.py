from __future__ import annotations

import uuid
from pathlib import Path

from doc2rag.chunking import Chunk, build_chunks, embed_chunks
from doc2rag.config import Settings, get_settings
from doc2rag.ingestion.excel import load_excel_tables
from doc2rag.ingestion.loaders import detect_source_type, load_pages
from doc2rag.ingestion.preprocess import preprocess_page
from doc2rag.layout import LayoutDetector
from doc2rag.schema.canonical import (
    CanonicalDocument,
    Exam,
    Patient,
    ProcessingMeta,
    Section,
    SourceType,
    TestResult,
)
from doc2rag.schema.intermediate import OcrLine, OcrRegionResult, RawTable, RegionType
from doc2rag.structuring import get_structuring_client
from doc2rag.tables import reconstruct_table
from doc2rag.validation import validate_document


class DocumentPipeline:
    """Wires ingestion -> layout/OCR -> table reconstruction -> LLM
    structuring -> validation -> chunking -> embedding into a single call,
    per the pipeline design in docs/ARCHITECTURE.md.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._layout_detector = LayoutDetector(lang=self._settings.ocr_lang)
        self._structuring_client = get_structuring_client(self._settings)

    def process(self, path: Path) -> tuple[CanonicalDocument, list[Chunk]]:
        source_type = detect_source_type(path)
        document_id = str(uuid.uuid4())

        if source_type == SourceType.EXCEL:
            raw_tables = load_excel_tables(path)
            text_regions: list[OcrRegionResult] = []
        else:
            raw_tables, text_regions = self._process_scanned_pages(path)

        structured = self._structuring_client.structure(text_regions, raw_tables)
        document = _to_canonical_document(
            document_id, source_type, structured, self._structuring_client.model_name
        )
        document = validate_document(document, raw_tables)

        chunks = build_chunks(document)
        chunks = embed_chunks(chunks, self._settings)
        return document, chunks

    def _process_scanned_pages(self, path: Path) -> tuple[list[RawTable], list[OcrRegionResult]]:
        pages = load_pages(path, dpi=self._settings.pdf_render_dpi)
        raw_tables: list[RawTable] = []
        text_regions: list[OcrRegionResult] = []

        for page_index, page in enumerate(pages):
            processed = preprocess_page(page)
            regions = self._layout_detector.detect(processed)

            for region in regions:
                if region.region_type == RegionType.TABLE and region.table_html:
                    raw_tables.append(reconstruct_table(region.table_html, page=page_index))
                elif region.content:
                    lines = [OcrLine(text=region.content, confidence=1.0, bbox=region.bbox)]
                    text_regions.append(OcrRegionResult(region=region, lines=lines))

        return raw_tables, text_regions


def _to_canonical_document(
    document_id: str, source_type: SourceType, structured: dict, llm_model: str
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
        processing_meta=ProcessingMeta(llm_model=llm_model),
    )


def get_pipeline() -> DocumentPipeline:
    return DocumentPipeline(get_settings())
