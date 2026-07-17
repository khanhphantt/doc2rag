"""Standalone Gradio demo for doc2rag structure parsing.

Mirrors the layout of the PaddleOCR structure-parsing demo
(https://aistudio.baidu.com/paddleocr): upload a document on the left, get a
side-by-side visualization (bounding boxes drawn on the source), a rendered
Markdown view of the recovered structure, and the raw JSON on the right.

It reuses the shipped pipeline stages (Document AI extraction -> table
reconstruction -> LLM structuring -> validation/location resolution) directly,
so we can surface each spatial stage as its own overlay -- just like
PP-StructureV3's layout visualization.

Run:
    python scripts/gradio_app.py
Then open the printed local URL.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import gradio as gr
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # for sibling medical_advisor

import medical_advisor  # noqa: E402
from doc2rag.config import get_settings  # noqa: E402
from doc2rag.docai import DocAiClient, extract_document  # noqa: E402
from doc2rag.ingestion.excel import load_excel_tables  # noqa: E402
from doc2rag.ingestion.loaders import detect_source_type, mime_type_for  # noqa: E402
from doc2rag.pipeline import _to_canonical_document  # noqa: E402
from doc2rag.schema.canonical import CanonicalDocument, PageMeta, SourceType  # noqa: E402
from doc2rag.schema.intermediate import LocatedText, RawTable  # noqa: E402
from doc2rag.structuring import get_structuring_client  # noqa: E402
from doc2rag.structuring.location_resolver import resolve_locations  # noqa: E402
from doc2rag.tables import reconstruct_table_from_grid  # noqa: E402
from doc2rag.validation import validate_document  # noqa: E402

EXAMPLE_IMAGE = ROOT / "data" / "健康診断.png"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

# Distinct colors cycled per table (same palette as scripts/run_visualize.py).
PALETTE = [
    (230, 25, 75), (60, 180, 75), (0, 130, 200), (245, 130, 48),
    (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60),
    (250, 190, 190), (0, 128, 128), (170, 110, 40), (128, 0, 0),
]

# DroidSansFallback covers CJK but has NO Latin glyphs (they render as tofu
# boxes), and DejaVu is the reverse -- so labels that mix Japanese and ASCII
# (e.g. "HDLコレステロール", "γ-GTP", "T0.1") need per-character font fallback.
FONT_PATHS_CJK = [
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
FONT_PATHS_LATIN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]


def _load(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x3000 <= o <= 0x30FF      # CJK symbols, hiragana, katakana
        or 0x3400 <= o <= 0x9FFF   # CJK unified ideographs (+ ext A)
        or 0xF900 <= o <= 0xFAFF   # CJK compatibility ideographs
        or 0xFF00 <= o <= 0xFFEF   # halfwidth/fullwidth forms
    )


class Font:
    """A CJK + Latin font pair that draws each character with whichever face
    actually has the glyph, so mixed Japanese/ASCII labels don't render tofu."""

    def __init__(self, size: int) -> None:
        self.cjk = _load(FONT_PATHS_CJK, size)
        self.latin = _load(FONT_PATHS_LATIN, size)

    def _for(self, ch: str) -> ImageFont.FreeTypeFont:
        return self.cjk if _is_cjk(ch) else self.latin

    def measure(self, draw, text: str) -> tuple[float, float]:
        w = h = 0.0
        for ch in text:
            f = self._for(ch)
            w += draw.textlength(ch, font=f)
            bb = draw.textbbox((0, 0), ch, font=f)
            h = max(h, bb[3] - bb[1])
        return w, h

    def draw(self, draw, xy, text: str, fill) -> None:
        x, y = xy
        for ch in text:
            f = self._for(ch)
            draw.text((x, y), ch, fill=fill, font=f)
            x += draw.textlength(ch, font=f)


def _font(size: int) -> Font:
    return Font(size)


def _poly(location, w: int, h: int):
    """Location (normalized 0-1 vertices) -> pixel polygon point list."""
    if location is None:
        return None
    return [(v.x * w, v.y * h) for v in location.vertices]


def _bbox(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def _draw_box(draw, poly, color, label, font: Font, width=3):
    draw.polygon(poly, outline=color, width=width)
    if label:
        x0, y0, _, _ = _bbox(poly)
        tw, th = font.measure(draw, label)
        draw.rectangle([x0, y0 - th - 4, x0 + tw + 4, y0], fill=color)
        font.draw(draw, (x0 + 2, y0 - th - 3), label, (255, 255, 255))


# --------------------------------------------------------------------------- viz
def _viz_docai_tables(img: Image.Image, table_grids) -> Image.Image:
    viz = img.copy()
    d = ImageDraw.Draw(viz)
    f = _font(15)
    W, H = img.size
    for ti, (_page_index, grid) in enumerate(table_grids):
        color = PALETTE[ti % len(PALETTE)]
        for row in grid:
            for cell in row:
                poly = _poly(cell.location, W, H)
                if poly:
                    _draw_box(d, poly, color, f"T{ti}", f, width=2)
    return viz


def _viz_reconstructed(img: Image.Image, raw_tables) -> Image.Image:
    viz = img.copy()
    d = ImageDraw.Draw(viz)
    f = _font(15)
    W, H = img.size
    for ti, t in enumerate(raw_tables):
        color = PALETTE[ti % len(PALETTE)]
        for ri, r in enumerate(t.rows):
            poly = _poly(r.item.location, W, H)
            if poly:
                _draw_box(d, poly, color, f"T{ti}.{ri}", f, width=2)
    return viz


def _viz_located(img: Image.Image, document: CanonicalDocument) -> Image.Image:
    viz = img.copy()
    d = ImageDraw.Draw(viz)
    f = _font(15)
    W, H = img.size
    idx = 0
    for s in document.sections:
        for r in s.results:
            poly = _poly(r.location, W, H)
            if poly:
                color = (200, 30, 30) if r.needs_review else (30, 160, 30)
                _draw_box(d, poly, color, f"{idx}", f, width=2)
            idx += 1
    return viz


# --------------------------------------------------------------------- markdown
def _canonical_markdown(document: CanonicalDocument) -> str:
    md: list[str] = ["# 健康診断 — Structure Parsing Result", ""]
    p = document.patient
    e = document.exam
    md.append(f"- **document_id**: `{document.document_id}`")
    md.append(f"- **source_type**: {document.source_type.value}")
    md.append(f"- **patient**: {p.name} · DOB {p.dob} · {p.gender} · ID {p.employee_id}")
    md.append(f"- **exam**: {e.date} @ {e.facility} ({e.exam_type})")
    md.append(f"- **overall_judgement**: {document.overall_judgement}")
    md.append(f"- **doctor_comment**: {document.doctor_comment}")
    md.append(f"- **needs_review**: {'⚠️ yes' if document.needs_review() else 'no'}")
    md.append("")
    for s in document.sections:
        md.append(f"## {s.category} — {len(s.results)} results\n")
        if s.free_text:
            md.append(f"> {s.free_text}\n")
        md.append("| # | item | value | unit | reference | judgement | located | review |")
        md.append("|---|------|-------|------|-----------|-----------|:-------:|:------:|")
        for i, r in enumerate(s.results):
            located = "✅" if r.location else "—"
            review = "⚠️" if r.needs_review else ""
            md.append(
                f"| {i} | {r.item} | {r.value or ''} | {r.unit or ''} "
                f"| {r.reference_range or ''} | {r.judgement or ''} | {located} | {review} |"
            )
        md.append("")
    if document.processing_meta.flags:
        md.append("## ⚠️ Validation flags\n")
        for fl in document.processing_meta.flags:
            md.append(f"- {fl}")
        md.append("")
    return "\n".join(md)


# ----------------------------------------------------------------------- engine
_settings = None
_docai = None
_structuring = None


def _lazy_clients():
    """Build clients once, lazily, so import/UI launch doesn't require keys."""
    global _settings, _docai, _structuring
    if _settings is None:
        _settings = get_settings()
        _docai = DocAiClient(_settings)
        _structuring = get_structuring_client(_settings)
    return _settings, _docai, _structuring


def parse_document(file_path: str | None):
    """Run the parsing pipeline and return (tables_viz, items_viz, located_viz,
    markdown, json_str, summary, document_dict)."""
    if not file_path:
        return None, None, None, "", "", "Please upload a document first.", None

    path = Path(file_path)
    settings, docai, structuring = _lazy_clients()

    source_type = detect_source_type(path)
    source_img: Image.Image | None = None
    if path.suffix.lower() in IMAGE_SUFFIXES:
        source_img = Image.open(path).convert("RGB")

    # --- extract -> reconstruct ------------------------------------------------
    if source_type == SourceType.EXCEL:
        raw_tables: list[RawTable] = load_excel_tables(path)
        paragraphs: list[LocatedText] = []
        pages: list[PageMeta] = []
        table_grids = []
    else:
        docai_doc = docai.process(path.read_bytes(), mime_type_for(path))
        extracted = extract_document(docai_doc)
        table_grids = extracted.table_grids
        raw_tables = [
            reconstruct_table_from_grid(grid, page=page_index)
            for page_index, grid in table_grids
        ]
        paragraphs = extracted.paragraphs
        pages = extracted.pages

    # --- structure -> validate -> locate --------------------------------------
    structured = structuring.structure(paragraphs, raw_tables)
    document = _to_canonical_document(
        str(uuid.uuid4()), source_type, structured, structuring.model_name, pages
    )
    document = validate_document(document, raw_tables)
    document = resolve_locations(document, structured, raw_tables)

    # --- render ----------------------------------------------------------------
    tables_viz = items_viz = located_viz = None
    if source_img is not None:
        tables_viz = _viz_docai_tables(source_img, table_grids)
        items_viz = _viz_reconstructed(source_img, raw_tables)
        located_viz = _viz_located(source_img, document)

    doc_dict = document.model_dump()
    markdown = _canonical_markdown(document)
    json_str = json.dumps(doc_dict, ensure_ascii=False, indent=2)

    n_results = sum(len(s.results) for s in document.sections)
    n_located = sum(1 for s in document.sections for r in s.results if r.location)
    summary = (
        f"✅ model={structuring.model_name} · source={source_type.value} · "
        f"tables={len(raw_tables)} · sections={len(document.sections)} · "
        f"results={n_results} · located={n_located} · "
        f"needs_review={document.needs_review()}"
    )
    return tables_viz, items_viz, located_viz, markdown, json_str, summary, doc_dict


def analyze_health(document_dict: dict | None):
    """Feature 2-4: LLM medical advisor + Tokyo hospital recommendations."""
    if not document_dict:
        return "_Parse a document first, then click **Analyze health & find hospitals**._"
    try:
        return medical_advisor.build_advice_markdown(document_dict)
    except Exception as exc:  # noqa: BLE001 - surface errors in the UI
        return f"⚠️ Analysis failed: `{exc}`"


# --------------------------------------------------------------------------- UI
def build_demo() -> gr.Blocks:
    with gr.Blocks(title="doc2rag — Structure Parsing") as demo:
        gr.Markdown(
            "# 📄 doc2rag — Document Structure Parsing\n"
            "Upload a Japanese health-checkup document (PDF / image / Excel). "
            "The pipeline runs **Document AI OCR → table reconstruction → LLM "
            "structuring → validation → location resolution** and returns the "
            "recovered structure with bounding-box overlays, Markdown, and JSON."
        )
        with gr.Row():
            with gr.Column(scale=1):
                file_in = gr.File(
                    label="Document",
                    file_types=[
                        ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff",
                        ".bmp", ".xlsx", ".xlsm",
                    ],
                    type="filepath",
                )
                run_btn = gr.Button("🔍 Parse structure", variant="primary")
                if EXAMPLE_IMAGE.exists():
                    gr.Examples(
                        examples=[[str(EXAMPLE_IMAGE)]],
                        inputs=file_in,
                        label="Example",
                    )
                status = gr.Markdown("")
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.Tab("🟩 Located results"):
                        located_out = gr.Image(label="Final located test results", type="pil")
                    with gr.Tab("🔤 Reconstructed items"):
                        items_out = gr.Image(label="Reconstructed table rows", type="pil")
                    with gr.Tab("🗂 DocAI tables"):
                        tables_out = gr.Image(label="Document AI table cells", type="pil")
                    with gr.Tab("📝 Markdown"):
                        md_out = gr.Markdown()
                    with gr.Tab("{ } JSON"):
                        json_out = gr.Code(language="json", label="CanonicalDocument")

        # Holds the parsed CanonicalDocument dict for the downstream advisor.
        doc_state = gr.State()

        # ---- Feature 2-4: medical advice + hospital finder (below the photo) ----
        gr.Markdown("---")
        advice_btn = gr.Button(
            "🩺 Analyze health & find Tokyo hospitals", variant="secondary"
        )
        advice_out = gr.Markdown()

        run_btn.click(
            fn=parse_document,
            inputs=file_in,
            outputs=[tables_out, items_out, located_out, md_out, json_out, status, doc_state],
        )
        advice_btn.click(fn=analyze_health, inputs=doc_state, outputs=advice_out)
    return demo


if __name__ == "__main__":
    build_demo().launch(theme=gr.themes.Soft())
