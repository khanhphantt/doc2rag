from __future__ import annotations

from pydantic import BaseModel, Field

# Mirrors CANONICAL_DOCUMENT_RESPONSE_SCHEMA's shape (item/value/unit/reference_range/
# judgement/source_row_id - no source_confidence/needs_review/location, which
# validation.py and location_resolver.py compute, not the LLM) but as Pydantic
# models, since Gemini's structured output accepts a Pydantic model directly
# as response_schema instead of a hand-written JSON Schema.


class LlmTestResult(BaseModel):
    item: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    judgement: str | None = None
    source_row_id: str | None = None


class LlmSection(BaseModel):
    category: str
    results: list[LlmTestResult] = Field(default_factory=list)
    free_text: str | None = None


class LlmPatient(BaseModel):
    name: str | None = None
    dob: str | None = None
    gender: str | None = None
    employee_id: str | None = None


class LlmExam(BaseModel):
    date: str | None = None
    facility: str | None = None
    exam_type: str | None = None


class LlmStructuredOutput(BaseModel):
    patient: LlmPatient
    exam: LlmExam
    sections: list[LlmSection] = Field(default_factory=list)
    overall_judgement: str | None = None
    doctor_comment: str | None = None
