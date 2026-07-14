# Hand-written JSON Schema for LLM structured-output calls (OpenAI "strict"
# mode requires additionalProperties: false and every property listed in
# "required", with optionality expressed via a nullable type instead of
# omission) — this intentionally does not reuse
# CanonicalDocument.model_json_schema() since pydantic's default output
# doesn't satisfy those strict-mode constraints.

_TEST_RESULT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["item", "value", "unit", "reference_range", "judgement"],
    "properties": {
        "item": {"type": "string"},
        "value": {"type": ["string", "null"]},
        "unit": {"type": ["string", "null"]},
        "reference_range": {"type": ["string", "null"]},
        "judgement": {"type": ["string", "null"]},
    },
}

_SECTION = {
    "type": "object",
    "additionalProperties": False,
    "required": ["category", "results", "free_text"],
    "properties": {
        "category": {"type": "string"},
        "results": {"type": "array", "items": _TEST_RESULT},
        "free_text": {"type": ["string", "null"]},
    },
}

CANONICAL_DOCUMENT_RESPONSE_SCHEMA = {
    "name": "canonical_health_checkup_document",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["patient", "exam", "sections", "overall_judgement", "doctor_comment"],
        "properties": {
            "patient": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "dob", "gender", "employee_id"],
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "dob": {"type": ["string", "null"]},
                    "gender": {"type": ["string", "null"]},
                    "employee_id": {"type": ["string", "null"]},
                },
            },
            "exam": {
                "type": "object",
                "additionalProperties": False,
                "required": ["date", "facility", "exam_type"],
                "properties": {
                    "date": {"type": ["string", "null"]},
                    "facility": {"type": ["string", "null"]},
                    "exam_type": {"type": ["string", "null"]},
                },
            },
            "sections": {"type": "array", "items": _SECTION},
            "overall_judgement": {"type": ["string", "null"]},
            "doctor_comment": {"type": ["string", "null"]},
        },
    },
}
