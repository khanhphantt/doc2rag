from __future__ import annotations

import json
from typing import Protocol

from doc2rag.config import Settings, get_settings
from doc2rag.schema.intermediate import LocatedText, RawTable
from doc2rag.structuring.llm_output_schema import LlmStructuredOutput
from doc2rag.structuring.prompts import SYSTEM_PROMPT, build_structuring_prompt
from doc2rag.structuring.response_schema import CANONICAL_DOCUMENT_RESPONSE_SCHEMA


class StructuringClient(Protocol):
    model_name: str

    def structure(self, text_regions: list[LocatedText], tables: list[RawTable]) -> dict:
        """Return a dict matching CANONICAL_DOCUMENT_RESPONSE_SCHEMA."""
        ...


class OpenAIStructuringClient:
    def __init__(self, settings: Settings) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key)
        self.model_name = settings.openai_model

    def structure(self, text_regions: list[LocatedText], tables: list[RawTable]) -> dict:
        user_prompt = build_structuring_prompt(text_regions, tables)
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_schema", "json_schema": CANONICAL_DOCUMENT_RESPONSE_SCHEMA},
        )
        return json.loads(response.choices[0].message.content)


class GeminiStructuringClient:
    """Pluggable alternative provider. Uses Gemini's JSON response-schema mode
    (a Pydantic model passed directly as response_schema, unlike OpenAI's
    hand-written strict-mode JSON Schema in response_schema.py).
    """

    def __init__(self, settings: Settings) -> None:
        from google import genai

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model

    def structure(self, text_regions: list[LocatedText], tables: list[RawTable]) -> dict:
        from google.genai import types

        user_prompt = build_structuring_prompt(text_regions, tables)
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LlmStructuredOutput,
            ),
        )
        return json.loads(response.text)


def get_structuring_client(settings: Settings | None = None) -> StructuringClient:
    settings = settings or get_settings()
    if settings.llm_provider == "openai":
        return OpenAIStructuringClient(settings)
    if settings.llm_provider == "gemini":
        return GeminiStructuringClient(settings)
    raise ValueError(f"Unknown llm_provider: {settings.llm_provider}")
