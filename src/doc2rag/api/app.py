"""HTTP API for the PaddleOCR-VL document-parsing core.

Endpoints:
  GET  /health       -> liveness
  POST /parse        -> parse a PDF/image into Markdown + per-page blocks (with
                        bbox and page images) + ready-to-embed interactive HTML
  POST /parse-excel  -> detect stacked tables in an .xlsx/.xlsm workbook and
                        return RAG-ready records + Markdown
  POST /advise       -> medical-advisor + Tokyo hospital recommendations (Markdown)

The legacy Document AI + LLM pipeline (doc2rag.pipeline) is retained in the
codebase but is no longer exposed here; PaddleOCR-VL is the baseline engine.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from doc2rag.vl import (
    INTERACTIVE_CSS,
    INTERACTIVE_HEAD,
    ParseOptions,
    build_interactive_html,
    get_parser,
)
from doc2rag.vl.render import IMAGE_SUFFIXES

SUPPORTED_SUFFIXES = {".pdf", *IMAGE_SUFFIXES}


class AdviceRequest(BaseModel):
    markdown: str | None = None
    document: dict | None = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="doc2rag",
        description="Parse documents into Markdown + structured JSON with an "
        "interactive layout view, powered by PaddleOCR-VL.",
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/parse")
    async def parse(
        file: UploadFile = File(...),
        options: str = Form("{}"),
        include_images: bool = Form(True),
        include_html: bool = Form(True),
    ) -> dict:
        """Parse a document. `options` is a JSON object matching ParseOptions."""
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
        try:
            opts = ParseOptions(**json.loads(options or "{}"))
        except Exception as exc:  # noqa: BLE001 - report bad options as 400
            raise HTTPException(status_code=400, detail=f"Invalid options: {exc}") from exc

        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp.flush()
            result = get_parser().parse(
                Path(tmp.name), opts, include_images=include_images
            )

        payload = {
            "markdown": result.markdown,
            "model_version": result.model_version,
            "num_blocks": result.num_blocks,
            "pages": [p.model_dump() for p in result.pages],
        }
        if include_html:
            payload["interactive_html"] = build_interactive_html(result)
            payload["assets"] = {"css": INTERACTIVE_CSS, "head_js": INTERACTIVE_HEAD}
        return payload

    @app.post("/parse-excel")
    async def parse_excel(file: UploadFile = File(...)) -> dict:
        """Detect stacked tables in an .xlsx/.xlsm workbook (no model weights /
        GPU needed). Returns per-table RAG-ready records + a Markdown rendering."""
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".xlsx", ".xlsm"}:
            raise HTTPException(status_code=400, detail=f"Expected .xlsx/.xlsm, got: {suffix}")

        from doc2rag.excel import parse_workbook

        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp.flush()
            return parse_workbook(Path(tmp.name))

    @app.post("/advise")
    def advise(req: AdviceRequest) -> dict:
        """Medical-advisor + Tokyo hospital recommendations for a parsed document."""
        from doc2rag.advisor import build_advice_markdown

        document = req.markdown if req.markdown is not None else req.document
        if not document:
            raise HTTPException(status_code=400, detail="Provide `markdown` or `document`.")
        return {"advice_markdown": build_advice_markdown(document)}

    return app


app = create_app()
