from __future__ import annotations

from doc2rag.chunking.chunker import Chunk
from doc2rag.config import Settings, get_settings

_GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"


def embed_chunks(chunks: list[Chunk], settings: Settings | None = None) -> list[Chunk]:
    """Embed each chunk's text in place and return the same list.

    Follows settings.llm_provider so switching providers covers both
    structuring and embedding with one setting; swap the model used per
    provider if the target MongoDB Atlas Vector Search index expects a
    specific one (see docs/ARCHITECTURE.md open items).
    """
    if not chunks:
        return chunks

    settings = settings or get_settings()
    if settings.llm_provider == "gemini":
        return _embed_with_gemini(chunks, settings)
    return _embed_with_openai(chunks, settings)


def _embed_with_openai(chunks: list[Chunk], settings: Settings) -> list[Chunk]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=settings.embedding_model, input=[c.text for c in chunks])
    for chunk, embedding_data in zip(chunks, response.data):
        chunk.embedding = embedding_data.embedding
    return chunks


def _embed_with_gemini(chunks: list[Chunk], settings: Settings) -> list[Chunk]:
    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.embed_content(model=_GEMINI_EMBEDDING_MODEL, contents=[c.text for c in chunks])
    for chunk, embedding in zip(chunks, response.embeddings):
        chunk.embedding = embedding.values
    return chunks
