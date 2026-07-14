from __future__ import annotations

from pydantic import BaseModel, Field

from doc2rag.schema.canonical import CanonicalDocument, Section


class ChunkMetadata(BaseModel):
    document_id: str
    patient_id: str | None = None
    exam_date: str | None = None
    facility: str | None = None
    category: str
    needs_review: bool = False


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata
    embedding: list[float] | None = Field(default=None, repr=False)


def build_chunks(document: CanonicalDocument) -> list[Chunk]:
    """One chunk per section (results serialized to natural language + free
    text), plus one document-level summary chunk, each carrying metadata for
    Mongo-side filtering (patient/date/facility/category).
    """
    chunks = [_section_chunk(document, section) for section in document.sections]
    chunks.append(_summary_chunk(document))
    return chunks


def _section_chunk(document: CanonicalDocument, section: Section) -> Chunk:
    lines = [f"【{section.category}】"]
    for result in section.results:
        line = f"{result.item}: {result.value or '不明'}"
        if result.unit:
            line += f" {result.unit}"
        if result.reference_range:
            line += f"(基準値: {result.reference_range})"
        if result.judgement:
            line += f" 判定: {result.judgement}"
        lines.append(line)
    if section.free_text:
        lines.append(section.free_text)

    return Chunk(
        text="\n".join(lines),
        metadata=ChunkMetadata(
            document_id=document.document_id,
            patient_id=document.patient.employee_id,
            exam_date=document.exam.date,
            facility=document.exam.facility,
            category=section.category,
            needs_review=any(r.needs_review for r in section.results),
        ),
    )


def _summary_chunk(document: CanonicalDocument) -> Chunk:
    lines = [
        f"健診日: {document.exam.date or '不明'}",
        f"実施機関: {document.exam.facility or '不明'}",
        f"総合判定: {document.overall_judgement or '不明'}",
    ]
    if document.doctor_comment:
        lines.append(f"医師所見: {document.doctor_comment}")

    return Chunk(
        text="\n".join(lines),
        metadata=ChunkMetadata(
            document_id=document.document_id,
            patient_id=document.patient.employee_id,
            exam_date=document.exam.date,
            facility=document.exam.facility,
            category="summary",
            needs_review=document.needs_review(),
        ),
    )
