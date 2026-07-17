"""Data models for the PaddleOCR-VL parsing core.

`ParseOptions` mirrors the knobs the demo exposes and maps 1:1 onto PaddleOCR-VL
`predict()` / `restructure_pages()` parameters. `ParseResult` (pages of blocks +
Markdown) is the single output shape shared by the HTTP API and the Gradio demo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Auxiliary-content option field -> PaddleOCR-VL layout label. By default all of
# these labels are filtered (in markdown_ignore_labels); flipping an option to
# True removes its label from the ignore list so the content is parsed.
AUX_LABELS: list[tuple[str, str]] = [
    ("parse_header", "header"),
    ("parse_header_image", "header_image"),
    ("parse_footer", "footer"),
    ("parse_footer_image", "footer_image"),
    ("parse_page_number", "number"),
    ("parse_footnote", "footnote"),
    ("parse_aside_text", "aside_text"),
]

LayoutShape = Literal["auto", "rect", "quad", "poly"]
PromptType = Literal["ocr", "formula", "table", "chart", "seal", "spotting"]


class ParseOptions(BaseModel):
    """Every parsing knob, with the same defaults as the aistudio demo."""

    # --- auxiliary content parsing (default: filtered out) ---
    parse_header: bool = False
    parse_header_image: bool = False
    parse_footer: bool = False
    parse_footer_image: bool = False
    parse_page_number: bool = False
    parse_footnote: bool = False
    parse_aside_text: bool = False

    # --- model parameter settings ---
    orientation_correction: bool = False
    distortion_correction: bool = False
    layout_analysis: bool = True
    chart_recognition: bool = False
    seal_recognition: bool = True
    image_text_recognition: bool = False
    merge_tables_across_pages: bool = True
    paragraph_title_recognition: bool = True
    layout_shape: LayoutShape = "auto"
    prompt_type: PromptType = "ocr"
    repetition_penalty: float = Field(1.0, ge=1.0, le=2.0)
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    min_pixels: int = Field(147384, ge=1)
    max_pixels: int = Field(2822400, ge=1)
    nms: bool = True

    def ignore_labels(self) -> list[str]:
        """Layout labels to keep filtered out of the Markdown output."""
        return [label for field, label in AUX_LABELS if not getattr(self, field)]

    def predict_kwargs(self) -> dict:
        """Map options onto PaddleOCR-VL `predict()` keyword arguments."""
        return {
            "use_doc_orientation_classify": self.orientation_correction,
            "use_doc_unwarping": self.distortion_correction,
            "use_layout_detection": self.layout_analysis,
            "use_chart_recognition": self.chart_recognition,
            "use_seal_recognition": self.seal_recognition,
            "use_ocr_for_image_block": self.image_text_recognition,
            "layout_nms": self.nms,
            "layout_shape_mode": self.layout_shape,
            "prompt_label": self.prompt_type,
            "repetition_penalty": self.repetition_penalty,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "min_pixels": self.min_pixels,
            "max_pixels": self.max_pixels,
            "markdown_ignore_labels": self.ignore_labels(),
        }


class Block(BaseModel):
    """One detected layout region."""

    id: int                       # stable per-page index (used for UI linking)
    order: int | None = None      # reading order (may be None)
    label: str                    # e.g. text, table, doc_title, image
    content: str                  # plain text, or HTML for tables
    bbox: list[float]             # [x0, y0, x1, y1] in page pixels


class Page(BaseModel):
    index: int                    # 0-based page index
    width: float
    height: float
    blocks: list[Block]
    image: str | None = None      # background as a data: URI (optional)


class ParseResult(BaseModel):
    """Full parse output: Markdown + per-page blocks (the API/demo payload)."""

    markdown: str
    pages: list[Page]
    model_version: str = "v1.6"

    @property
    def num_blocks(self) -> int:
        return sum(len(p.blocks) for p in self.pages)
