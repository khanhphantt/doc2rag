"""Rendering helpers for the PaddleOCR-VL core: page rasterization, and the
self-contained interactive HTML (hover a region <-> highlight its parsed block).

`INTERACTIVE_CSS` and `INTERACTIVE_HEAD` must be injected into the host page
(the Gradio demo passes them to `launch(css=..., head=...)`; an HTTP client can
inline them). `build_interactive_html(result)` returns the body markup.
"""

from __future__ import annotations

import base64
import html as html_lib
import io
from pathlib import Path

from PIL import Image

from doc2rag.vl.models import ParseResult

MAX_BG_WIDTH = 1600  # downscale the interactive background; boxes are placed by %
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

INTERACTIVE_CSS = """
.pp-root { font-size: 13px; }
.pp-hint { opacity: .7; margin: 2px 0 10px; }
.pp-pagehdr { font-weight: 600; margin: 10px 0 4px; opacity: .7; }
.pp-wrap { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 16px; }
.pp-image { position: relative; flex: 3 1 0; min-width: 0; line-height: 0; }
.pp-image img { width: 100%; display: block;
  border: 1px solid var(--border-color-primary, #ccc); border-radius: 6px; }
.pp-box { position: absolute; box-sizing: border-box;
  border: 2px solid rgba(56,132,255,.5); background: rgba(56,132,255,.05);
  border-radius: 2px; cursor: pointer; transition: background .08s, border-color .08s; }
.pp-box .pp-tag { position: absolute; top: -15px; left: -1px; font-size: 10px;
  line-height: 14px; padding: 0 4px; background: rgba(56,132,255,.9); color: #fff;
  white-space: nowrap; border-radius: 3px 3px 0 0; opacity: 0; pointer-events: none; }
.pp-box.pp-on { border-color: #ff453a; background: rgba(255,69,58,.2); z-index: 6; }
.pp-box.pp-on .pp-tag { opacity: 1; background: #ff453a; }
.pp-list { flex: 2 1 0; min-width: 0; max-height: 660px; overflow: auto; padding-right: 4px; }
.pp-item { padding: 6px 9px; margin-bottom: 5px;
  border: 1px solid var(--border-color-primary, #ddd);
  border-left: 3px solid rgba(56,132,255,.7); border-radius: 5px; cursor: pointer;
  background: var(--background-fill-secondary, transparent); }
.pp-item.pp-on { border-left-color: #ff453a; box-shadow: 0 0 0 1px #ff453a inset; }
.pp-hd { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 2px; }
.pp-lbl { font-weight: 700; font-size: 10px; letter-spacing: .03em;
  text-transform: uppercase; color: rgb(56,132,255); }
.pp-item.pp-on .pp-lbl { color: #ff453a; }
.pp-ord { font-size: 10px; opacity: .6; }
.pp-txt { color: var(--body-text-color, inherit); white-space: pre-wrap;
  word-break: break-word; max-height: 130px; overflow: auto; font-size: 12px; }
.pp-html { color: var(--body-text-color, inherit); max-height: 320px; overflow: auto; font-size: 11px; }
.pp-html table { border-collapse: collapse; width: 100%; }
.pp-html td, .pp-html th { border: 1px solid var(--border-color-primary, #ccc);
  padding: 2px 5px; text-align: center; word-break: break-word; }

/* settings + hover "?" tooltips (aistudio-style) */
.pp-set { display: flex; align-items: center; gap: 6px; min-height: 30px; font-size: 13px; }
.pp-tip { display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; border: 1px solid var(--border-color-primary, #999);
  border-radius: 50%; font-size: 10px; line-height: 1; cursor: help;
  color: var(--body-text-color, inherit); opacity: .65; position: relative; flex: none; }
.pp-tip:hover, .pp-tip:focus { opacity: 1; border-color: #3884ff; outline: none; }
.pp-tip::after { content: attr(data-tip); position: absolute; left: 0; bottom: 135%;
  min-width: 180px; max-width: 300px; background: #1f2937; color: #fff;
  padding: 6px 9px; border-radius: 6px; font-size: 11px; line-height: 1.45;
  text-align: left; white-space: normal; opacity: 0; pointer-events: none;
  transition: opacity .12s; z-index: 60; box-shadow: 0 2px 10px rgba(0,0,0,.35); }
.pp-tip:hover::after, .pp-tip:focus::after { opacity: 1; }
.pp-aux-desc { opacity: .7; font-size: 12px; margin: 0 0 6px; }
"""

# One delegated listener (attached once) links every element sharing a data-pp
# id, so it keeps working for HTML injected after a parse.
INTERACTIVE_HEAD = """
<script>
(function () {
  function toggle(id, on) {
    document.querySelectorAll('[data-pp="' + id + '"]').forEach(function (e) {
      e.classList.toggle('pp-on', on);
    });
  }
  document.addEventListener('mouseover', function (ev) {
    var t = ev.target.closest ? ev.target.closest('[data-pp]') : null;
    if (!t) return;
    var id = t.getAttribute('data-pp');
    toggle(id, true);
    if (t.classList.contains('pp-box')) {
      var li = document.querySelector('.pp-item[data-pp="' + id + '"]');
      if (li) li.scrollIntoView({ block: 'nearest' });
    }
  }, true);
  document.addEventListener('mouseout', function (ev) {
    var t = ev.target.closest ? ev.target.closest('[data-pp]') : null;
    if (!t) return;
    toggle(t.getAttribute('data-pp'), false);
  }, true);
})();
</script>
"""


def page_images(file_path: str | Path, n: int) -> list[Image.Image | None]:
    """Clean background raster per page (boxes are positioned by %, so the exact
    pixel size doesn't matter). PDFs via pypdfium2; images opened directly."""
    path = Path(file_path)
    imgs: list[Image.Image | None] = []
    if path.suffix.lower() == ".pdf":
        try:
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(str(path))
            for i in range(min(n, len(pdf))):
                imgs.append(pdf[i].render(scale=2).to_pil().convert("RGB"))
        except Exception:  # noqa: BLE001 - rasterization is best-effort
            imgs = []
    else:
        try:
            imgs = [Image.open(path).convert("RGB")]
        except Exception:  # noqa: BLE001
            imgs = []
    imgs += [None] * (n - len(imgs))
    return imgs[:n]


def image_data_uri(img: Image.Image) -> str:
    """PNG data: URI, downscaled to MAX_BG_WIDTH for size."""
    if img.width > MAX_BG_WIDTH:
        h = round(img.height * MAX_BG_WIDTH / img.width)
        img = img.resize((MAX_BG_WIDTH, h))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def build_interactive_html(result: ParseResult) -> str:
    """Self-contained hover-linked page/region + block-list markup for a result.

    Requires INTERACTIVE_CSS and INTERACTIVE_HEAD to be present on the host page.
    """
    parts = [
        '<div class="pp-root">',
        '<div class="pp-hint">Hover a region on the page to highlight the parsed '
        "block on the right — and vice-versa.</div>",
    ]
    multi = len(result.pages) > 1
    for page in result.pages:
        w = page.width or 1.0
        h = page.height or 1.0
        if multi:
            parts.append(
                f'<div class="pp-pagehdr">Page {page.index + 1} — {len(page.blocks)} blocks</div>'
            )
        parts.append('<div class="pp-wrap">')

        if page.image:
            parts.append(f'<div class="pp-image"><img src="{page.image}">')
            for b in page.blocks:
                bid = f"{page.index}-{b.id}"
                x0, y0, x1, y1 = (b.bbox + [0, 0, 0, 0])[:4]
                left = max(0.0, x0 / w * 100)
                top = max(0.0, y0 / h * 100)
                bw = max(0.0, (x1 - x0) / w * 100)
                bh = max(0.0, (y1 - y0) / h * 100)
                order = b.order if b.order is not None else b.id
                parts.append(
                    f'<div class="pp-box" data-pp="{bid}" '
                    f'style="left:{left:.2f}%;top:{top:.2f}%;width:{bw:.2f}%;height:{bh:.2f}%">'
                    f'<span class="pp-tag">#{order} {html_lib.escape(b.label)}</span></div>'
                )
            parts.append("</div>")

        parts.append('<div class="pp-list">')
        ordered = sorted(page.blocks, key=lambda b: (b.order if b.order is not None else 1 << 30))
        for b in ordered:
            bid = f"{page.index}-{b.id}"
            order = b.order if b.order is not None else b.id
            if b.content.lstrip().startswith("<"):  # tables / HTML: render as-is
                body = f'<div class="pp-txt pp-html">{b.content}</div>'
            else:
                disp = html_lib.escape(b.content[:600]) + ("…" if len(b.content) > 600 else "")
                body = f'<div class="pp-txt">{disp}</div>'
            parts.append(
                f'<div class="pp-item" data-pp="{bid}">'
                f'<div class="pp-hd"><span class="pp-lbl">{html_lib.escape(b.label)}</span>'
                f'<span class="pp-ord">#{order}</span></div>'
                f"{body}</div>"
            )
        parts.append("</div></div>")  # pp-list, pp-wrap
    parts.append("</div>")  # pp-root
    return "".join(parts)
