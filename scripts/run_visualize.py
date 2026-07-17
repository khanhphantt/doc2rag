"""Run the doc2rag pipeline stage-by-stage against a health-checkup image,
dumping the intermediate result of every stage as JSON + Markdown and
rendering a bounding-box visualization for each spatial stage.

Stages (mirrors docs/ARCHITECTURE.md):
  1. Document AI extraction   -> table grids + paragraphs (+ viz)
  2. Table reconstruction     -> item/value/unit/reference/judgement rows (+ viz)
  3. LLM structuring          -> canonical-shaped dict
  4. Validation + location    -> CanonicalDocument (+ located-item viz)

Outputs land in data/output/. Nothing here is part of the shipped pipeline;
this is the visual sanity-check driver called for in ARCHITECTURE open item #8.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from doc2rag.config import get_settings  # noqa: E402
from doc2rag.docai import DocAiClient, extract_document  # noqa: E402
from doc2rag.ingestion.loaders import detect_source_type, mime_type_for  # noqa: E402
from doc2rag.pipeline import _to_canonical_document  # noqa: E402
from doc2rag.schema.canonical import SourceType  # noqa: E402
from doc2rag.structuring import get_structuring_client  # noqa: E402
from doc2rag.structuring.location_resolver import resolve_locations  # noqa: E402
from doc2rag.tables import reconstruct_table_from_grid  # noqa: E402
from doc2rag.validation import validate_document  # noqa: E402

IMAGE_PATH = ROOT / "data" / "健康診断.png"
OUT = ROOT / "data" / "output"
OUT.mkdir(parents=True, exist_ok=True)
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

# distinct-ish colors cycled per table
PALETTE = [
    (230, 25, 75), (60, 180, 75), (0, 130, 200), (245, 130, 48),
    (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60),
    (250, 190, 190), (0, 128, 128), (170, 110, 40), (128, 0, 0),
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


def _label(text: str, limit: int = 14) -> str:
    """One-line, length-capped label for drawing over a box."""
    flat = " ".join(text.split())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  wrote {name}")


def main() -> None:
    print(f"Input: {IMAGE_PATH.name}")
    img = Image.open(IMAGE_PATH).convert("RGB")
    W, H = img.size
    source_type = detect_source_type(IMAGE_PATH)
    assert source_type == SourceType.IMAGE

    # ---------------------------------------------------------------- Stage 1
    print("\n[1] Document AI extraction ...")
    settings = get_settings()
    docai = DocAiClient(settings)
    docai_doc = docai.process(IMAGE_PATH.read_bytes(), mime_type_for(IMAGE_PATH))
    extracted = extract_document(docai_doc)

    stage1 = {
        "pages": [p.model_dump() for p in extracted.pages],
        "num_tables": len(extracted.table_grids),
        "num_paragraphs": len(extracted.paragraphs),
        "tables": [
            {
                "table_index": ti,
                "page": page_index,
                "num_rows": len(grid),
                "rows": [[c.model_dump() for c in row] for row in grid],
            }
            for ti, (page_index, grid) in enumerate(extracted.table_grids)
        ],
        "paragraphs": [p.model_dump() for p in extracted.paragraphs],
    }
    dump("01_docai_extraction.json", stage1)
    print(f"  {len(extracted.table_grids)} tables, {len(extracted.paragraphs)} paragraphs")

    # viz: every cell of every table, colored per table
    viz = img.copy()
    d = ImageDraw.Draw(viz)
    f = _font(15)
    for ti, (page_index, grid) in enumerate(extracted.table_grids):
        color = PALETTE[ti % len(PALETTE)]
        for ri, row in enumerate(grid):
            for ci, cell in enumerate(row):
                poly = _poly(cell.location, W, H)
                if poly:
                    _draw_box(d, poly, color, f"T{ti}", f, width=2)
    viz.save(OUT / "01_docai_tables_viz.png")
    print("  wrote 01_docai_tables_viz.png")

    # viz: paragraphs
    viz2 = img.copy()
    d2 = ImageDraw.Draw(viz2)
    for pi, para in enumerate(extracted.paragraphs):
        poly = _poly(para.location, W, H)
        if poly:
            _draw_box(d2, poly, (0, 130, 200), f"P{pi}", f, width=2)
    viz2.save(OUT / "01_docai_paragraphs_viz.png")
    print("  wrote 01_docai_paragraphs_viz.png")

    # ---------------------------------------------------------------- Stage 2
    print("\n[2] Table reconstruction ...")
    raw_tables = [
        reconstruct_table_from_grid(grid, page=page_index)
        for page_index, grid in extracted.table_grids
    ]
    total_rows = sum(len(t.rows) for t in raw_tables)
    stage2 = {
        "num_tables": len(raw_tables),
        "total_rows": total_rows,
        "tables": [
            {
                "table_index": ti,
                "page": t.page,
                "rows": [
                    {
                        "id": r.item.id,
                        "item": r.item.text,
                        "value": r.value.text if r.value else None,
                        "unit": r.unit.text if r.unit else None,
                        "reference_range": r.reference_range.text if r.reference_range else None,
                        "judgement": r.judgement.text if r.judgement else None,
                        "confidence": r.confidence,
                    }
                    for r in t.rows
                ],
            }
            for ti, t in enumerate(raw_tables)
        ],
    }
    dump("02_reconstructed_tables.json", stage2)

    # markdown table dump (every item across every table)
    md = ["# Stage 2 — Reconstructed table rows", ""]
    md.append(f"**{len(raw_tables)} tables, {total_rows} rows total**\n")
    for tinfo in stage2["tables"]:
        md.append(f"## Table {tinfo['table_index']} (page {tinfo['page']}) — {len(tinfo['rows'])} rows\n")
        md.append("| id | item | value | unit | reference | judgement | conf |")
        md.append("|----|------|-------|------|-----------|-----------|------|")
        for r in tinfo["rows"]:
            md.append(
                f"| {r['id']} | {r['item'] or ''} | {r['value'] or ''} | {r['unit'] or ''} "
                f"| {r['reference_range'] or ''} | {r['judgement'] or ''} | {r['confidence']:.2f} |"
            )
        md.append("")
    (OUT / "02_reconstructed_tables.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  {total_rows} rows across {len(raw_tables)} tables; wrote 02_reconstructed_tables.{{json,md}}")

    # viz: reconstructed item cells, labeled with the Japanese item name
    viz3 = img.copy()
    d3 = ImageDraw.Draw(viz3)
    fj = _font(17)
    for ti, t in enumerate(raw_tables):
        color = PALETTE[ti % len(PALETTE)]
        for ri, r in enumerate(t.rows):
            poly = _poly(r.item.location, W, H)
            if poly:
                _draw_box(d3, poly, color, _label(r.item.text), fj, width=2)
    viz3.save(OUT / "02_reconstructed_items_viz.png")
    print("  wrote 02_reconstructed_items_viz.png")

    # ---------------------------------------------------------------- Stage 3
    print("\n[3] LLM structuring ...")
    client = get_structuring_client(settings)
    structured = client.structure(extracted.paragraphs, raw_tables)
    dump("03_llm_structured.json", structured)
    n_results = sum(len(s["results"]) for s in structured["sections"])
    print(f"  model={client.model_name}, {len(structured['sections'])} sections, {n_results} results")

    # ---------------------------------------------------------------- Stage 4
    print("\n[4] Validation + location resolution ...")
    import uuid
    document = _to_canonical_document(
        str(uuid.uuid4()), source_type, structured, client.model_name, extracted.pages
    )
    document = validate_document(document, raw_tables)
    document = resolve_locations(document, structured, raw_tables)
    dump("04_canonical.json", document.model_dump())
    print(f"  needs_review={document.needs_review()}, flags={len(document.processing_meta.flags)}")

    # canonical markdown export
    md = [f"# 健康診断 — canonical extraction", ""]
    md.append(f"- **document_id**: {document.document_id}")
    md.append(f"- **source_type**: {document.source_type.value}")
    p = document.patient
    md.append(f"- **patient**: {p.name} / DOB {p.dob} / {p.gender} / ID {p.employee_id}")
    e = document.exam
    md.append(f"- **exam**: {e.date} @ {e.facility} ({e.exam_type})")
    md.append(f"- **overall_judgement**: {document.overall_judgement}")
    md.append(f"- **doctor_comment**: {document.doctor_comment}")
    md.append(f"- **needs_review**: {document.needs_review()}")
    md.append("")
    located = 0
    for s in document.sections:
        md.append(f"## {s.category} — {len(s.results)} results\n")
        if s.free_text:
            md.append(f"> {s.free_text}\n")
        md.append("| item | value | unit | reference | judgement | located | review |")
        md.append("|------|-------|------|-----------|-----------|---------|--------|")
        for r in s.results:
            has_loc = "yes" if r.location else "—"
            if r.location:
                located += 1
            md.append(
                f"| {r.item} | {r.value or ''} | {r.unit or ''} | {r.reference_range or ''} "
                f"| {r.judgement or ''} | {has_loc} | {'⚠' if r.needs_review else ''} |"
            )
        md.append("")
    if document.processing_meta.flags:
        md.append("## Validation flags\n")
        for fl in document.processing_meta.flags:
            md.append(f"- {fl}")
        md.append("")
    (OUT / "04_canonical.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  {n_results} results, {located} with resolved location; wrote 04_canonical.{{json,md}}")

    # viz: final located test results
    viz4 = img.copy()
    d4 = ImageDraw.Draw(viz4)
    fj4 = _font(17)
    for s in document.sections:
        for r in s.results:
            poly = _poly(r.location, W, H)
            if poly:
                color = (200, 30, 30) if r.needs_review else (30, 160, 30)
                _draw_box(d4, poly, color, _label(r.item), fj4, width=2)
    viz4.save(OUT / "04_located_items_viz.png")
    print("  wrote 04_located_items_viz.png")

    # summary
    print("\n==== SUMMARY ====")
    print(f"tables (docai):        {len(extracted.table_grids)}")
    print(f"paragraphs:            {len(extracted.paragraphs)}")
    print(f"reconstructed rows:    {total_rows}")
    print(f"canonical results:     {n_results}")
    print(f"located results:       {located}")
    print(f"validation flags:      {len(document.processing_meta.flags)}")
    print(f"outputs in:            {OUT}")


if __name__ == "__main__":
    main()
