"""Standalone Gradio demo: parse a *native* (digital, not scanned) PDF into
Markdown + RAG-ready JSON with **Docling** (IBM's deep-learning document parser,
TableFormer table model), with special handling for the two table layouts that
break naive extractors:

  * **stacked tables on one page** — several tables sitting side-by-side
    (horizontal) or above/below each other (vertical). Docling recovers each as
    its own table; this demo orders them into reading order (row-band, then
    left-to-right) and draws a colour-coded page overlay.
  * **tables that span multiple pages** — a table whose body continues onto the
    next page(s). Docling emits these as separate tables; this demo **stitches**
    them back into ONE logical table when the column count matches and the
    continuation has no header (or repeats the header).

This is the PDF sibling of ``scripts/gradio_excel_tables.py`` (same job for
spreadsheets). For each detected table it emits page span, per-page bounding
box(es), inferred header, data rows, a Markdown rendering, and a structured JSON
record (ready for RAG chunking) — plus Docling's full-document Markdown export.

Why Docling?  For *native* PDFs — especially **borderless / visually complex**
tables (financial sheets, spreadsheet exports) — Docling's TableFormer model
reconstructs structure that ruled-line parsers (pdfplumber, PyMuPDF) miss. It
runs locally, needs no cloud API, and reads values from the PDF's real text
layer (``do_cell_matching``), so numbers are never hallucinated. On a CUDA GPU
it parses a page in ~1-2 s.

Recommended config (used below): ``do_ocr=False`` (native PDF — skip OCR),
``TableFormerMode.ACCURATE`` (borderless tables need the full model),
``do_cell_matching=True`` (exact values from the text layer), accelerator auto =
CUDA if a GPU is present else CPU.

Run:
    python scripts/gradio_pdf_tables.py
Then open the printed local URL.

Requires: ``pip install docling`` plus a torch build (CUDA recommended:
``pip install torch --index-url https://download.pytorch.org/whl/cu124``).
Also uses gradio + pillow + pypdfium2 (already project deps). LLM cleanup is
optional and reuses the project's provider settings.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import gradio as gr
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Distinct colours cycled per logical table (mirrors the Excel demo palette).
PALETTE = [
    (230, 25, 75), (60, 180, 75), (0, 130, 200), (245, 130, 48),
    (145, 30, 180), (70, 200, 200), (240, 50, 230), (160, 190, 40),
    (250, 150, 150), (0, 128, 128), (170, 110, 40), (128, 0, 0),
]

# Render zoom for the page overlays (2.0 ~= 144 dpi: crisp but light).
RENDER_ZOOM = 2.0

# Cross-page stitch tolerances, as fractions of page height: a table must END in
# the bottom band of its page and the continuation must START in the top band.
BOTTOM_BAND = 0.80    # y1 must be below this fraction of page height
TOP_BAND = 0.28       # y0 must be above this fraction of page height

# Two tables on the same page belong to the same reading-order ROW BAND when
# their tops are within this fraction of page height — used to order side-by-side
# (horizontally stacked) tables left-to-right.
ROW_BAND = 0.06


# ----------------------------------------------------------------- data model
class PhysTable:
    """One table as Docling detected it on a single page (a *physical* table).
    Cross-page continuations are separate PhysTables until stitched."""

    def __init__(self, page_index: int, page_height: float, bbox, header,
                 rows: list[list[str]]):
        self.page_index = page_index
        self.page_height = page_height
        self.bbox = tuple(round(v, 1) for v in bbox)   # (x0, y0, x1, y1), TL origin
        self.header = header                            # list[str] | None
        self.header_external = False                    # Docling headers are in-body
        self.rows = rows                                # data rows (header excluded)

    @property
    def col_count(self) -> int:
        if self.header:
            return len(self.header)
        return max((len(r) for r in self.rows), default=0)

    def ends_at_bottom(self) -> bool:
        return self.bbox[3] >= BOTTOM_BAND * self.page_height

    def starts_at_top(self) -> bool:
        return self.bbox[1] <= TOP_BAND * self.page_height


def _clean(v) -> str:
    if v is None:
        return ""
    return " ".join(str(v).split())


def _norm_header(h: list[str]) -> tuple:
    """A comparable fingerprint for a header row (case/space-insensitive)."""
    return tuple(_clean(x).lower() for x in h)


# ------------------------------------------------------------- Docling backend
# The DocumentConverter loads deep-learning weights on first use, so we build it
# once and reuse it across parses.
_CONVERTER = None
_DEVICE = None


def _get_converter():
    """Build (once) a DocumentConverter tuned for *native* (digital),
    table-dense PDFs:

      * ``do_ocr=False``             — real text layer, so skip OCR (speed + no
        OCR guesses on already-perfect text).
      * ``TableFormerMode.ACCURATE`` — borderless tables need the full model.
      * ``do_cell_matching=True``    — snap the PDF's actual text cells into the
        predicted grid, so values come from the document, never invented.
      * accelerator = CUDA if a GPU/torch is present, else CPU (auto-detected).
    """
    global _CONVERTER, _DEVICE
    if _CONVERTER is not None:
        return _CONVERTER, _DEVICE

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        AcceleratorDevice, AcceleratorOptions, PdfPipelineOptions, TableFormerMode,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    device = AcceleratorDevice.CPU
    try:
        import torch

        if torch.cuda.is_available():
            device = AcceleratorDevice.CUDA
    except Exception:  # noqa: BLE001 — torch optional; fall back to CPU
        pass

    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = True
    opts.table_structure_options.mode = TableFormerMode.ACCURATE
    opts.table_structure_options.do_cell_matching = True
    opts.accelerator_options = AcceleratorOptions(num_threads=8, device=device)

    _CONVERTER = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )
    _DEVICE = device.value
    return _CONVERTER, _DEVICE


def _grid_text(data) -> list[list[str]]:
    """Docling's table grid as a dense num_rows × num_cols text matrix (spans are
    already expanded into every covered cell)."""
    out = []
    for r in range(data.num_rows):
        row = data.grid[r]
        out.append([_clean(row[c].text) if c < len(row) else ""
                    for c in range(data.num_cols)])
    return out


def _header_row_count(data) -> int:
    """Number of leading rows Docling flagged as column headers."""
    n = 0
    for r in range(data.num_rows):
        flags = [data.grid[r][c].column_header for c in range(data.num_cols)
                 if c < len(data.grid[r])]
        if flags and sum(flags) >= max(1, 0.5 * data.num_cols):
            n = r + 1
        else:
            break
    return n


def _to_phys(table, page_heights: dict[int, float]) -> PhysTable | None:
    """Convert one Docling TableItem into a PhysTable, or None if unusable."""
    if not table.prov:
        return None
    prov = table.prov[0]
    page_index = prov.page_no - 1
    ph = page_heights.get(prov.page_no, 0.0)
    tl = prov.bbox.to_top_left_origin(page_height=ph)   # (l, t, r, b), t < b
    bbox = (tl.l, tl.t, tl.r, tl.b)

    grid = _grid_text(table.data)
    if table.data.num_cols < 2 or table.data.num_rows < 2:
        return None

    hn = _header_row_count(table.data)
    if hn == 0:
        header = None
        body = grid
    else:
        # Combine multi-row headers per column (join top→bottom, collapse repeats).
        header = []
        for c in range(table.data.num_cols):
            parts: list[str] = []
            for r in range(hn):
                v = grid[r][c]
                if v and (not parts or parts[-1] != v):
                    parts.append(v)
            header.append(" ".join(parts))
        body = grid[hn:]

    rows = [r for r in body if any(r)]
    if not rows and header is None:
        return None
    return PhysTable(page_index, ph, bbox, header, rows)


def _extract(doc) -> tuple[list[list[PhysTable]], int]:
    """Return (tables grouped by page in reading order, page_count)."""
    page_heights = {pno: pg.size.height for pno, pg in doc.pages.items()}
    n_pages = max(page_heights) if page_heights else 0
    by_page: list[list[PhysTable]] = [[] for _ in range(n_pages)]
    for table in doc.tables:
        pt = _to_phys(table, page_heights)
        if pt is None or not (0 <= pt.page_index < n_pages):
            continue
        by_page[pt.page_index].append(pt)
    for pi in range(n_pages):
        ph = page_heights.get(pi + 1, 0.0)
        by_page[pi] = _reading_order(by_page[pi], ph)
    return by_page, n_pages


def _reading_order(tables: list[PhysTable], page_height: float) -> list[PhysTable]:
    """Sort tables into human reading order. Tables whose tops fall in the same
    horizontal band (side-by-side / horizontally stacked) are read left→right;
    bands themselves go top→bottom."""
    band = max(1.0, ROW_BAND * page_height)
    return sorted(tables, key=lambda t: (round(t.bbox[1] / band), t.bbox[0]))


# ---------------------------------------------------- cross-page table stitching
def _stitch(all_tables: list[list[PhysTable]], enabled: bool) -> list[dict]:
    """Merge physical tables that are really one table split across pages.

    A logical table is a run of PhysTables where each continuation:
      * is the TOP-most table of its page and starts in the top band,
      * follows a predecessor that is the BOTTOM-most table of its page and
        ends in the bottom band,
      * has the same column count, and
      * either carries no header, or repeats the predecessor's header
        (repeated header rows are dropped from the continuation's data)."""
    logical: list[dict] = []
    open_tbl: dict | None = None

    for page_index, page_tables in enumerate(all_tables):
        for pos, pt in enumerate(page_tables):
            is_first_on_page = pos == 0
            is_last_on_page = pos == len(page_tables) - 1

            can_continue = (
                enabled
                and open_tbl is not None
                and is_first_on_page
                and pt.starts_at_top()
                and open_tbl["_prev_ends_bottom"]
                and open_tbl["_prev_last_on_page"]
                and open_tbl["_prev_page"] == page_index - 1
                and pt.col_count == open_tbl["col_count"]
            )
            if can_continue:
                cont_rows = pt.rows
                repeated = (
                    pt.header is not None
                    and open_tbl["header_raw"] is not None
                    and _norm_header(pt.header) == _norm_header(open_tbl["header_raw"])
                )
                if pt.header is not None and not repeated:
                    # A continuation with a *different* header-looking first row:
                    # keep it as data rather than silently dropping it.
                    cont_rows = [pt.header] + pt.rows
                open_tbl["rows"].extend(cont_rows)
                open_tbl["parts"].append({"page": page_index, "bbox": list(pt.bbox),
                                          "repeated_header": repeated})
                open_tbl["pages"].append(page_index)
            else:
                open_tbl = _new_logical(pt)
                logical.append(open_tbl)

            open_tbl["_prev_ends_bottom"] = pt.ends_at_bottom()
            open_tbl["_prev_last_on_page"] = is_last_on_page
            open_tbl["_prev_page"] = page_index

    for i, lt in enumerate(logical):
        lt["color"] = PALETTE[i % len(PALETTE)]
        for k in ("_prev_ends_bottom", "_prev_last_on_page", "_prev_page",
                  "header_raw"):
            lt.pop(k, None)
    return logical


def _new_logical(pt: PhysTable) -> dict:
    header = pt.header or [f"col_{i + 1}" for i in range(pt.col_count)]
    header = _uniquify([h or f"col_{i + 1}" for i, h in enumerate(header)])
    return {
        "pages": [pt.page_index],
        "header": header,
        "header_raw": pt.header,          # pre-uniquify, for continuation matching
        "col_count": pt.col_count,
        "rows": list(pt.rows),
        "parts": [{"page": pt.page_index, "bbox": list(pt.bbox),
                   "repeated_header": False}],
    }


def _uniquify(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for h in headers:
        n = seen.get(h, 0) + 1
        seen[h] = n
        out.append(h if n == 1 else f"{h}_{n}")
    return out


def _records(lt: dict) -> list[dict]:
    header = lt["header"]
    w = len(header)
    recs = []
    for row in lt["rows"]:
        row = (list(row) + [""] * w)[:w]
        recs.append(dict(zip(header, row)))
    return recs


# ------------------------------------------------------- page overlay rendering
def _font(size: int):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _render_overlays(pdf_path: Path, n_pages: int,
                     logical: list[dict]) -> list[Image.Image]:
    """One image per page with every logical table's box drawn in its colour and
    labelled `T{n}` (and `(cont.)` for a continued part)."""
    per_page: dict[int, list[tuple]] = {}
    for ti, lt in enumerate(logical):
        for part in lt["parts"]:
            per_page.setdefault(part["page"], []).append((ti, lt, part))

    images = []
    font = _font(22)
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        for pno in range(min(n_pages, len(pdf))):
            img = pdf[pno].render(scale=RENDER_ZOOM).to_pil().convert("RGB")
            draw = ImageDraw.Draw(img, "RGBA")
            for ti, lt, part in per_page.get(pno, []):
                x0, y0, x1, y1 = (v * RENDER_ZOOM for v in part["bbox"])
                col = lt["color"]
                draw.rectangle([x0, y0, x1, y1], outline=col, width=3,
                               fill=col + (28,))
                is_cont = part is not lt["parts"][0]
                label = f"T{ti + 1}" + (" (cont.)" if is_cont else "")
                tw = draw.textlength(label, font=font)
                draw.rectangle([x0, max(0, y0 - 26), x0 + tw + 10, y0], fill=col)
                draw.text((x0 + 5, max(0, y0 - 25)), label, fill=(255, 255, 255),
                          font=font)
            images.append(img)
    finally:
        pdf.close()
    return images


# ------------------------------------------------------------- markdown / json
def _md_table(header: list[str], rows: list[list[str]]) -> str:
    def esc(s: str) -> str:
        return _clean(s).replace("|", "\\|")

    w = len(header)
    out = ["| " + " | ".join(esc(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        row = (list(row) + [""] * w)[:w]
        out.append("| " + " | ".join(esc(c) for c in row) + " |")
    return "\n".join(out)


def _page_span(lt: dict) -> str:
    pages = sorted(set(lt["pages"]))
    if len(pages) == 1:
        return f"p.{pages[0] + 1}"
    return f"pp.{pages[0] + 1}–{pages[-1] + 1}"


def _markdown(logical: list[dict], fname: str) -> str:
    md = [f"# {fname} — detected tables", ""]
    spanning = sum(1 for lt in logical if len(set(lt["pages"])) > 1)
    md.append(
        f"Detected **{len(logical)}** logical table(s); "
        f"**{spanning}** span multiple pages.\n"
    )
    for i, lt in enumerate(logical):
        span = _page_span(lt)
        desc = f" — {lt['description']}" if lt.get("description") else ""
        md.append(f"## Table {i + 1} `[{span}]`{desc}\n")
        if lt.get("merge_note"):
            flag = "✅" if lt.get("merge_ok", True) else "⚠️"
            md.append(f"> {flag} {lt['merge_note']}\n")
        if len(set(lt["pages"])) > 1:
            md.append(f"> 🔗 stitched across pages {span} "
                      f"({len(lt['parts'])} fragments).\n")
        md.append(_md_table(lt["header"], lt["rows"]))
        md.append("")
    return "\n".join(md)


def _json_payload(logical: list[dict], fname: str) -> list[dict]:
    payload = []
    for i, lt in enumerate(logical):
        payload.append({
            "source": fname,
            "table_index": i,
            "pages": sorted(set(p + 1 for p in lt["pages"])),
            "spans_pages": len(set(lt["pages"])) > 1,
            "description": lt.get("description"),
            "merge_verified": lt.get("merge_ok"),
            "n_rows": len(lt["rows"]),
            "n_cols": len(lt["header"]),
            "headers": lt["header"],
            "parts": [
                {"page": p["page"] + 1, "bbox": p["bbox"],
                 "repeated_header": p["repeated_header"]}
                for p in lt["parts"]
            ],
            "records": _records(lt),
        })
    return payload


# ------------------------------------------------------------------ optional LLM
# OPT-IN cleanup on top of the deterministic parser (never the default path).
# Two independent tasks, each cached by content hash so re-runs cost nothing:
#   1. DESCRIBE     — one-line RAG description per logical table.
#   2. VERIFY MERGE — for tables that span pages, confirm the stitch was correct.
# Structure-only; no cell values are ever taken from the model.
_CACHE_PATH = Path(tempfile.gettempdir()) / "doc2rag_pdf_llm_cache.json"


def _load_cache() -> dict:
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(cache: dict) -> None:
    try:
        _CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass


def _parse_json(text: str | None):
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        i, j = text.find("{"), text.rfind("}")
        if 0 <= i < j:
            try:
                return json.loads(text[i:j + 1])
            except ValueError:
                return None
    return None


class CheapLLM:
    """Thin provider-agnostic JSON client reusing the project's settings but
    defaulting to the cheap model tier. Disables itself gracefully."""

    OPENAI_MODEL = "gpt-4o-mini"
    GEMINI_MODEL = "gemini-1.5-flash"

    def __init__(self) -> None:
        self.log: list[str] = []
        self.calls = 0
        self._provider = None
        self._client = None
        self.model = None
        self._cache = _load_cache()
        try:
            from doc2rag.config import get_settings

            s = get_settings()
        except Exception as exc:  # noqa: BLE001
            self.log.append(f"⚠️ LLM off — settings unavailable: `{exc}`")
            return
        self._provider = s.llm_provider
        try:
            if s.llm_provider == "openai":
                if not s.openai_api_key:
                    raise RuntimeError("no OpenAI API key configured")
                from openai import OpenAI

                self._client = OpenAI(api_key=s.openai_api_key)
                self.model = self.OPENAI_MODEL
            elif s.llm_provider == "gemini":
                if not s.gemini_api_key:
                    raise RuntimeError("no Gemini API key configured")
                from google import genai

                self._client = genai.Client(api_key=s.gemini_api_key)
                self.model = self.GEMINI_MODEL
            else:
                raise RuntimeError(f"unknown provider {s.llm_provider!r}")
        except Exception as exc:  # noqa: BLE001
            self.log.append(f"⚠️ LLM off — {exc}")
            self._client = None

    @property
    def ready(self) -> bool:
        return self._client is not None

    def _complete(self, system: str, user: str, kind: str):
        key = hashlib.sha1(f"{kind}|{self.model}|{system}|{user}".encode()).hexdigest()
        if key in self._cache:
            self.log.append(f"• {kind}: cache hit (no API call)")
            return self._cache[key]
        self.calls += 1
        try:
            if self._provider == "openai":
                r = self._client.chat.completions.create(
                    model=self.model, temperature=0,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                )
                text = r.choices[0].message.content
            else:
                from google.genai import types

                r = self._client.models.generate_content(
                    model=self.model, contents=f"{system}\n\n{user}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"),
                )
                text = r.text
        except Exception as exc:  # noqa: BLE001
            self.log.append(f"• {kind}: API call failed — `{exc}`")
            return None
        data = _parse_json(text)
        if data is not None:
            self._cache[key] = data
            _save_cache(self._cache)
        return data

    def describe(self, lt: dict) -> str | None:
        preview = _records(lt)[:2]
        user = (
            "Write ONE concise sentence describing what this table contains, for "
            "retrieval context in a RAG system. Summarize; don't list every "
            "column.\n"
            f"headers: {lt['header']}\n"
            f"sample_rows: {preview}\n"
            'Return JSON {"description": "..."}.'
        )
        data = self._complete(
            "You write terse, factual one-sentence table summaries. Answer only "
            "with the requested JSON.", user, "describe")
        try:
            desc = str(data["description"]).strip()
        except (TypeError, KeyError):
            return None
        if desc:
            self.log.append(f"• describe: {desc[:60]}")
        return desc or None

    def verify_merge(self, lt: dict) -> None:
        """For a multi-page table, ask the model whether the continuation really
        is the same table. Annotates lt['merge_note'] / lt['merge_ok']."""
        pages = sorted(set(p + 1 for p in lt["pages"]))
        head_rows = lt["rows"][:3]
        tail_rows = lt["rows"][-3:]
        user = (
            "Two table fragments on consecutive PDF pages were merged into one "
            "table because their column counts matched and the second had no new "
            "header. Confirm this was correct (same table continuing) or flag a "
            "likely false merge.\n"
            f"pages: {pages}\n"
            f"headers: {lt['header']}\n"
            f"first_rows: {head_rows}\n"
            f"last_rows: {tail_rows}\n"
            'Return JSON {"same_table": bool, "explanation": "one short line"}.'
        )
        data = self._complete(
            "You audit whether two PDF table fragments are one continued table. "
            "Answer only with the requested JSON.", user, "verify_merge")
        if isinstance(data, dict) and "same_table" in data:
            lt["merge_ok"] = bool(data["same_table"])
            lt["merge_note"] = str(data.get("explanation") or "")
            flag = "✅" if lt["merge_ok"] else "⚠️ false merge?"
            self.log.append(f"• verify_merge {pages}: {flag} {lt['merge_note'][:50]}")


# --------------------------------------------------------------------------- engine
def parse_pdf(file_path: str | None, do_stitch: bool, use_describe: bool,
              use_verify: bool):
    """Return (summary, tables_markdown, json_str, gallery_images, llm_log,
    full_markdown, md_file, json_file)."""
    blank = ("", "", [], "", "", None, None)
    if not file_path:
        return ("Please upload a PDF first.", *blank)

    path = Path(file_path)
    try:
        converter, device = _get_converter()
    except Exception as exc:  # noqa: BLE001
        return (f"⚠️ Docling unavailable: `{exc}`\n\nInstall it with "
                "`pip install docling` (+ a torch build).", *blank)

    try:
        result = converter.convert(str(path))
        doc = result.document
    except Exception as exc:  # noqa: BLE001
        return (f"⚠️ Docling failed to parse the PDF: `{exc}`", *blank)

    all_tables, n_pages = _extract(doc)
    n_phys = sum(len(p) for p in all_tables)
    logical = _stitch(all_tables, enabled=do_stitch)

    # Optional LLM layer.
    use_llm = use_describe or use_verify
    llm = CheapLLM() if use_llm else None
    have_llm = llm is not None and llm.ready
    if have_llm:
        for lt in logical:
            if use_verify and len(set(lt["pages"])) > 1:
                llm.verify_merge(lt)
            if use_describe:
                lt["description"] = llm.describe(lt)

    images = _render_overlays(path, n_pages, logical)

    try:
        full_md = doc.export_to_markdown()
    except Exception as exc:  # noqa: BLE001
        full_md = f"_Docling markdown export failed: {exc}_"

    spanning = sum(1 for lt in logical if len(set(lt["pages"])) > 1)
    llm_bit = ""
    if use_llm:
        tasks = "+".join(t for t, on in (("describe", use_describe),
                                         ("verify", use_verify)) if on)
        llm_bit = (f" · LLM={llm.model} [{tasks}], calls={llm.calls}"
                   if have_llm else " · LLM=off (see log)")
    summary = (
        f"✅ {path.name} · pages={n_pages} · "
        f"physical tables={n_phys} → logical tables={len(logical)} "
        f"({spanning} span pages) · engine=Docling/TableFormer(ACCURATE) "
        f"· device={device}"
        f"{' · stitch=on' if do_stitch else ' · stitch=off'}{llm_bit}"
    )

    if not use_llm:
        llm_log = ("_LLM off. Enable **Describe** for a one-line RAG summary per "
                   "table, and/or **Verify merge** to have the model confirm each "
                   "cross-page stitch._")
    elif llm and llm.log:
        llm_log = "**LLM log**\n\n" + "\n".join(llm.log)
    elif have_llm:
        llm_log = "_LLM enabled — nothing needed describing / verifying._"
    else:
        llm_log = "_LLM could not start (missing key / provider)._"

    markdown = _markdown(logical, path.name)
    payload = _json_payload(logical, path.name)
    json_str = json.dumps(payload, ensure_ascii=False, indent=2)

    md_file = str(path.with_suffix(".pdf.tables.md"))
    json_file = str(path.with_suffix(".pdf.tables.json"))
    try:
        Path(md_file).write_text(markdown, encoding="utf-8")
        Path(json_file).write_text(json_str, encoding="utf-8")
    except OSError:
        md_file = json_file = None

    return (summary, markdown, json_str, images, llm_log, full_md,
            md_file, json_file)


# --------------------------------------------------------------------------- UI
_ABOUT = """\
### Why Docling for native (digital) PDFs?

Docling uses a deep-learning table model (**TableFormer**) that reconstructs
table structure even when the PDF has **no ruled lines** — the case that breaks
line-based parsers (pdfplumber, PyMuPDF). It runs **locally** (no cloud API) and
reads values from the PDF's **real text layer** (`do_cell_matching`), so numbers
are never hallucinated.

This demo runs Docling with: `do_ocr=False` (native PDF → skip OCR),
`TableFormerMode.ACCURATE`, `do_cell_matching=True`, accelerator auto = **CUDA**
if a GPU is present else CPU.

On top of Docling, this demo adds: **reading-order** ordering of stacked
tables, **cross-page stitching** (rejoin a table split across pages), a
colour-coded **page overlay**, and **RAG-ready JSON** records.

_Reach for a commercial API (Azure Document Intelligence, AWS Textract,
LlamaParse) only when you also have scanned pages or need SLA-grade accuracy at
scale. For a spreadsheet exported to PDF, parsing the original `.xlsx` beats any
PDF parser — see `scripts/gradio_excel_tables.py`._
"""


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Native PDF Table Parser (Docling)") as demo:
        gr.Markdown(
            "# 📄 Native PDF → Markdown + JSON — powered by Docling\n"
            "Upload a **digital (not scanned)** PDF. **Docling** (TableFormer) "
            "reconstructs every table — including **borderless** ones. This demo "
            "orders **stacked** tables (side-by-side or top/bottom) into reading "
            "order and **stitches tables that span multiple pages** back into "
            "one. Get a colour-coded page overlay, Markdown, and RAG-ready JSON.\n\n"
            "Two opt-in LLM tasks (cheap model, cached): **🤖 Describe** "
            "(one-line RAG summary per table) and **🔗 Verify merge** (confirm "
            "each cross-page stitch)."
        )
        with gr.Accordion("📚 About the engine & config", open=False):
            gr.Markdown(_ABOUT)
        with gr.Row():
            with gr.Column(scale=1):
                file_in = gr.File(label="PDF", file_types=[".pdf"], type="filepath")
                do_stitch = gr.Checkbox(
                    label="🔗 Stitch tables across pages", value=True)
                use_describe = gr.Checkbox(
                    label="🤖 LLM Describe — one-line summary per table",
                    value=False)
                use_verify = gr.Checkbox(
                    label="🔗 LLM Verify merge — confirm cross-page stitches",
                    value=False)
                run_btn = gr.Button("🔍 Parse PDF with Docling", variant="primary")
                status = gr.Markdown("")
                md_dl = gr.File(label="⬇ Markdown (.md)")
                json_dl = gr.File(label="⬇ JSON (.json)")
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.Tab("🗺 Page overlay"):
                        gallery = gr.Gallery(label="Detected tables per page",
                                             columns=1, height=680,
                                             object_fit="contain")
                    with gr.Tab("📝 Tables (Markdown)"):
                        md_out = gr.Markdown()
                    with gr.Tab("{ } JSON"):
                        json_out = gr.Code(language="json", label="Detected tables")
                    with gr.Tab("📄 Full document (Docling)"):
                        full_out = gr.Markdown()
                    with gr.Tab("🤖 LLM log"):
                        llm_out = gr.Markdown()

        run_btn.click(
            fn=parse_pdf,
            inputs=[file_in, do_stitch, use_describe, use_verify],
            outputs=[status, md_out, json_out, gallery, llm_out, full_out,
                     md_dl, json_dl],
        )
    return demo


if __name__ == "__main__":
    build_demo().launch(theme=gr.themes.Soft())
