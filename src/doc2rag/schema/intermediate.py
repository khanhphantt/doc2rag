from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class RegionType(str, Enum):
    TABLE = "table"
    TEXT = "text"
    TITLE = "title"


class LayoutRegion(BaseModel):
    region_type: RegionType
    bbox: BBox
    order: int
    table_html: str | None = None  # populated for RegionType.TABLE
    content: str | None = None  # PP-StructureV3's own recognized text, for TEXT/TITLE regions


class OcrLine(BaseModel):
    text: str
    confidence: float
    bbox: BBox


class OcrRegionResult(BaseModel):
    region: LayoutRegion
    lines: list[OcrLine] = Field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def min_confidence(self) -> float:
        return min((line.confidence for line in self.lines), default=1.0)


class RawTableRow(BaseModel):
    item_name: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    judgement: str | None = None
    confidence: float = 1.0


class RawTable(BaseModel):
    rows: list[RawTableRow] = Field(default_factory=list)
    page: int = 0
