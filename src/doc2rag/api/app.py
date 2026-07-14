from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

from doc2rag.pipeline import DocumentPipeline, get_pipeline
from doc2rag.storage import MongoChunkStore

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".xlsx", ".xlsm"}


@lru_cache
def _get_pipeline() -> DocumentPipeline:
    return get_pipeline()


@lru_cache
def _get_store() -> MongoChunkStore:
    return MongoChunkStore()


def create_app() -> FastAPI:
    app = FastAPI(title="doc2rag", description="Extract structured RAG-ready JSON from 健康診断 documents")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/process")
    async def process(file: UploadFile) -> dict:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp.flush()
            document, chunks = _get_pipeline().process(Path(tmp.name))

        _get_store().insert_chunks(chunks)

        return {
            "document": document.model_dump(),
            "needs_review": document.needs_review(),
            "chunk_count": len(chunks),
        }

    return app


app = create_app()
