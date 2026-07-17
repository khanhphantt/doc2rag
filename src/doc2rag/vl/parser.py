"""PaddleOCR-VL parsing engine — the project's core.

`VLParser.parse(path, options)` runs PaddleOCR-VL end-to-end and returns a
`ParseResult` (Markdown + per-page blocks with bounding boxes), the single
shape consumed by both the HTTP API and the Gradio demo.
"""

from __future__ import annotations

from pathlib import Path

from doc2rag.vl import render
from doc2rag.vl.models import Block, Page, ParseOptions, ParseResult

DEFAULT_PIPELINE_VERSION = "v1.6"


def _page_payload(res) -> dict:
    """PaddleOCR-VL nests the useful fields under a top-level 'res' key."""
    try:
        j = res.json
    except Exception:  # noqa: BLE001 - some backends expose .json lazily
        return {"error": "json unavailable for this page"}
    if isinstance(j, dict) and "res" in j and isinstance(j["res"], dict):
        return j["res"]
    return j if isinstance(j, dict) else {"res": j}


def _markdown_text(res) -> str:
    md = getattr(res, "markdown", None) or {}
    text = md.get("markdown_texts", "")
    if isinstance(text, list):
        text = "\n\n".join(str(t) for t in text)
    return text or ""


class VLParser:
    """Lazy singleton wrapper around the PaddleOCR-VL pipeline.

    All optional sub-modules are loaded up front so every option can be toggled
    per-`predict()` call without rebuilding the (expensive) pipeline.
    """

    def __init__(self, pipeline_version: str = DEFAULT_PIPELINE_VERSION) -> None:
        self.pipeline_version = pipeline_version
        self._pipeline = None

    def _pipeline_obj(self):
        if self._pipeline is None:
            from paddleocr import PaddleOCRVL  # imported lazily so imports stay cheap

            self._pipeline = PaddleOCRVL(
                pipeline_version=self.pipeline_version,
                use_doc_orientation_classify=True,
                use_doc_unwarping=True,
                use_chart_recognition=True,
                use_seal_recognition=True,
                use_ocr_for_image_block=True,
            )
        return self._pipeline

    def parse(
        self,
        file_path: str | Path,
        options: ParseOptions | None = None,
        *,
        include_images: bool = True,
    ) -> ParseResult:
        """Parse a PDF/image into Markdown + per-page blocks."""
        options = options or ParseOptions()
        pipeline = self._pipeline_obj()

        results = list(pipeline.predict(str(file_path), **options.predict_kwargs()))

        # cross-page restructuring (PDF only; no-op for a single page)
        if len(results) > 1 and (
            options.merge_tables_across_pages or options.paragraph_title_recognition
        ):
            results = list(
                pipeline.restructure_pages(
                    results,
                    merge_tables=options.merge_tables_across_pages,
                    relevel_titles=options.paragraph_title_recognition,
                )
            )

        imgs = (
            render.page_images(file_path, len(results))
            if include_images
            else [None] * len(results)
        )

        pages: list[Page] = []
        md_parts: list[str] = []
        for i, res in enumerate(results):
            payload = _page_payload(res)
            raw_blocks = payload.get("parsing_res_list", []) or []
            blocks = [
                Block(
                    id=idx,
                    order=b.get("block_order"),
                    label=str(b.get("block_label", "")),
                    content=str(b.get("block_content", "")),
                    bbox=[float(v) for v in (b.get("block_bbox") or [0, 0, 0, 0])[:4]],
                )
                for idx, b in enumerate(raw_blocks)
            ]
            img = imgs[i] if i < len(imgs) else None
            pages.append(
                Page(
                    index=i,
                    width=float(payload.get("width") or (img.width if img else 1) or 1),
                    height=float(payload.get("height") or (img.height if img else 1) or 1),
                    blocks=blocks,
                    image=render.image_data_uri(img) if img is not None else None,
                )
            )
            md_parts.append(_markdown_text(res))

        return ParseResult(
            markdown="\n\n---\n\n".join(p for p in md_parts if p),
            pages=pages,
            model_version=self.pipeline_version,
        )


_parser: VLParser | None = None


def get_parser() -> VLParser:
    """Process-wide singleton parser (pipeline version from Settings)."""
    global _parser
    if _parser is None:
        from doc2rag.config import get_settings

        _parser = VLParser(get_settings().vl_pipeline_version)
    return _parser
