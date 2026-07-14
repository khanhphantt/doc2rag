"""Quick standalone check that OPENAI_API_KEY / GEMINI_API_KEY in .env are valid.

Makes one cheap, read-only call per provider (list models) instead of running
anything through doc2rag's pipeline, so a bad key surfaces in seconds rather
than after several minutes of OCR processing.

Usage: python scripts/check_api_keys.py
"""

from __future__ import annotations

from doc2rag.config import get_settings


def check_openai(api_key: str) -> None:
    if not api_key:
        print("[OpenAI] SKIPPED - DOC2RAG_OPENAI_API_KEY is empty in .env")
        return

    from openai import OpenAI

    try:
        client = OpenAI(api_key=api_key)
        models = client.models.list()
        first_model = next(iter(models), None)
        print(f"[OpenAI] OK - key is valid (e.g. model: {first_model.id if first_model else 'n/a'})")
    except Exception as e:
        print(f"[OpenAI] FAILED - {type(e).__name__}: {e}")


def check_gemini(api_key: str) -> None:
    if not api_key:
        print("[Gemini] SKIPPED - DOC2RAG_GEMINI_API_KEY is empty in .env")
        return

    from google import genai

    try:
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        first_model = next(iter(models), None)
        print(f"[Gemini] OK - key is valid (e.g. model: {first_model.name if first_model else 'n/a'})")
    except Exception as e:
        print(f"[Gemini] FAILED - {type(e).__name__}: {e}")


if __name__ == "__main__":
    settings = get_settings()
    check_openai(settings.openai_api_key)
    check_gemini(settings.gemini_api_key)
