"""Redraw the stage-2 and stage-4 visualizations with Japanese item-name
labels, reusing the cached JSON in data/output/ (no Document AI / LLM calls)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from doc2rag.schema.intermediate import Location, LocatedText, NormalizedVertex  # noqa: E402
from doc2rag.tables import reconstruct_table_from_grid  # noqa: E402

OUT = ROOT / "data" / "output"
FONT = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
PALETTE = [
    (230, 25, 75), (60, 180, 75), (0, 130, 200), (245, 130, 48),
    (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60),
    (250, 190, 190), (0, 128, 128), (170, 110, 40), (128, 0, 0),
]


def font(sz):
    return ImageFont.truetype(FONT, sz)


def label(text, limit=14):
    flat = " ".join(text.split())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def poly(loc, w, h):
    if not loc:
        return None
    return [(v["x"] * w, v["y"] * h) for v in loc["vertices"]]


def loc_obj(loc):
    if not loc:
        return None
    return Location(page=loc["page"], vertices=[NormalizedVertex(**v) for v in loc["vertices"]])


def draw_box(d, pts, color, text, f, width=2):
    d.polygon(pts, outline=color, width=width)
    x0 = min(p[0] for p in pts)
    y0 = min(p[1] for p in pts)
    tb = d.textbbox((0, 0), text, font=f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.rectangle([x0, y0 - th - 5, x0 + tw + 4, y0], fill=color)
    d.text((x0 + 2, y0 - th - 4), text, fill=(255, 255, 255), font=f)


img = Image.open(ROOT / "data" / "健康診断.png").convert("RGB")
W, H = img.size
f = font(17)

# ---- stage 2: rebuild grids from cached extraction, reconstruct, redraw ----
extraction = json.loads((OUT / "01_docai_extraction.json").read_text(encoding="utf-8"))
grids = []
for tinfo in extraction["tables"]:
    grid = [
        [LocatedText(id=c["id"], text=c["text"], location=loc_obj(c["location"])) for c in row]
        for row in tinfo["rows"]
    ]
    grids.append((tinfo["page"], grid))

viz2 = img.copy()
d2 = ImageDraw.Draw(viz2)
for ti, (page, grid) in enumerate(grids):
    color = PALETTE[ti % len(PALETTE)]
    table = reconstruct_table_from_grid(grid, page=page)
    for r in table.rows:
        pts = poly(r.item.location.model_dump() if r.item.location else None, W, H)
        if pts:
            draw_box(d2, pts, color, label(r.item.text), f)
viz2.save(OUT / "02_reconstructed_items_viz.png")
print("wrote 02_reconstructed_items_viz.png")

# ---- stage 4: located canonical results, labeled with Japanese item name ----
canonical = json.loads((OUT / "04_canonical.json").read_text(encoding="utf-8"))
viz4 = img.copy()
d4 = ImageDraw.Draw(viz4)
for s in canonical["sections"]:
    for r in s["results"]:
        pts = poly(r["location"], W, H)
        if pts:
            color = (200, 30, 30) if r["needs_review"] else (30, 160, 30)
            draw_box(d4, pts, color, label(r["item"]), f)
viz4.save(OUT / "04_located_items_viz.png")
print("wrote 04_located_items_viz.png")
