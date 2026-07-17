from __future__ import annotations

from pathlib import Path

from doc2rag.schema.canonical import SourceType

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
EXCEL_SUFFIXES = {".xlsx", ".xlsm"}

_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
}


def detect_source_type(path: Path) -> SourceType:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return SourceType.PDF
    if suffix in EXCEL_SUFFIXES:
        return SourceType.EXCEL
    if suffix in IMAGE_SUFFIXES:
        return SourceType.IMAGE
    raise ValueError(f"Unsupported file type: {suffix}")


def mime_type_for(path: Path) -> str:
    """Document AI's process_document call needs an explicit MIME type
    alongside the raw file bytes - it does not sniff the file itself."""
    suffix = path.suffix.lower()
    if suffix not in _MIME_TYPES:
        raise ValueError(f"Unsupported file type for Document AI: {suffix}")
    return _MIME_TYPES[suffix]
