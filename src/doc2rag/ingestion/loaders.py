from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from doc2rag.schema.canonical import SourceType

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
EXCEL_SUFFIXES = {".xlsx", ".xlsm"}


def detect_source_type(path: Path) -> SourceType:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return SourceType.PDF
    if suffix in EXCEL_SUFFIXES:
        return SourceType.EXCEL
    if suffix in IMAGE_SUFFIXES:
        return SourceType.IMAGE
    raise ValueError(f"Unsupported file type: {suffix}")


def load_pages(path: Path, dpi: int = 300) -> list[np.ndarray]:
    """Load a document as a list of RGB page images (H, W, 3) uint8 arrays.

    Excel files are not rendered here; callers should detect SourceType.EXCEL
    upstream and route to the openpyxl-based parser instead of OCR.
    """
    source_type = detect_source_type(path)

    if source_type == SourceType.IMAGE:
        image = Image.open(path).convert("RGB")
        return [np.array(image)]

    if source_type == SourceType.PDF:
        return _render_pdf_pages(path, dpi)

    raise ValueError(f"load_pages does not handle source_type={source_type}; route Excel separately")


def _render_pdf_pages(path: Path, dpi: int) -> list[np.ndarray]:
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    pages: list[np.ndarray] = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            pages.append(image)
    return pages
