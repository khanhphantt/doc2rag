from doc2rag.chunking.chunker import build_chunks
from doc2rag.schema.canonical import CanonicalDocument, Exam, Patient, Section, SourceType, TestResult


def test_build_chunks_one_per_section_plus_summary():
    document = CanonicalDocument(
        document_id="doc-1",
        source_type=SourceType.IMAGE,
        patient=Patient(employee_id="E123"),
        exam=Exam(date="2026-07-01", facility="Tokyo Clinic"),
        overall_judgement="要経過観察",
        sections=[
            Section(category="身体計測", results=[TestResult(item="BMI", value="22.1")]),
            Section(category="血液検査", results=[TestResult(item="HbA1c", value="5.4", unit="%")]),
        ],
    )

    chunks = build_chunks(document)

    assert len(chunks) == 3  # 2 sections + 1 summary
    categories = [c.metadata.category for c in chunks]
    assert categories == ["身体計測", "血液検査", "summary"]
    assert all(c.metadata.document_id == "doc-1" for c in chunks)
    assert all(c.metadata.patient_id == "E123" for c in chunks)
    assert "BMI: 22.1" in chunks[0].text
    assert "要経過観察" in chunks[2].text


def test_needs_review_propagates_to_chunk_metadata():
    document = CanonicalDocument(
        document_id="doc-1",
        source_type=SourceType.IMAGE,
        sections=[
            Section(
                category="血液検査",
                results=[TestResult(item="HbA1c", value="5.4", needs_review=True)],
            )
        ],
    )

    chunks = build_chunks(document)

    assert chunks[0].metadata.needs_review is True
