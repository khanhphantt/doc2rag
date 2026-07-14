from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    EXCEL = "excel"


class Patient(BaseModel):
    name: str | None = None
    dob: str | None = None
    gender: str | None = None
    employee_id: str | None = None


class Exam(BaseModel):
    date: str | None = None
    facility: str | None = None
    exam_type: str | None = None


class TestResult(BaseModel):
    item: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    judgement: str | None = None
    source_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    needs_review: bool = False


class Section(BaseModel):
    category: str
    results: list[TestResult] = Field(default_factory=list)
    free_text: str | None = None


class ProcessingMeta(BaseModel):
    ocr_engine: str = "paddleocr"
    llm_model: str | None = None
    flags: list[str] = Field(default_factory=list)


class CanonicalDocument(BaseModel):
    document_id: str
    source_type: SourceType
    patient: Patient = Field(default_factory=Patient)
    exam: Exam = Field(default_factory=Exam)
    sections: list[Section] = Field(default_factory=list)
    overall_judgement: str | None = None
    doctor_comment: str | None = None
    processing_meta: ProcessingMeta = Field(default_factory=ProcessingMeta)

    def needs_review(self) -> bool:
        return any(r.needs_review for s in self.sections for r in s.results)
