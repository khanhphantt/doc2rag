from __future__ import annotations

from typing import Any

from pymongo import MongoClient

from doc2rag.chunking.chunker import Chunk
from doc2rag.config import Settings, get_settings


class MongoChunkStore:
    """Writes RAG chunks (text + embedding + metadata) to MongoDB.

    Embedding-model/index configuration (dimension, similarity metric) is
    assumed to match whatever the existing Atlas Vector Search index expects
    — see docs/ARCHITECTURE.md open items; this class only writes documents
    and does not manage the vector index itself.
    """

    def __init__(self, settings: Settings | None = None, client: MongoClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client or MongoClient(self._settings.mongo_uri)

    @property
    def _collection(self):
        return self._client[self._settings.mongo_db][self._settings.mongo_chunks_collection]

    def insert_chunks(self, chunks: list[Chunk]) -> list[Any]:
        if not chunks:
            return []
        documents = [
            {
                "text": chunk.text,
                "embedding": chunk.embedding,
                "metadata": chunk.metadata.model_dump(),
            }
            for chunk in chunks
        ]
        result = self._collection.insert_many(documents)
        return result.inserted_ids
