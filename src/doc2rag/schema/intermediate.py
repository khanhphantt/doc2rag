from __future__ import annotations

from pydantic import BaseModel, Field


class NormalizedVertex(BaseModel):
    x: float
    y: float


class Location(BaseModel):
    page: int
    vertices: list[NormalizedVertex]


class LocatedText(BaseModel):
    id: str
    text: str
    location: Location | None = None
    """None for rows with no visual position (e.g. Excel-sourced tables)."""


class RawTableRow(BaseModel):
    item: LocatedText
    value: LocatedText | None = None
    unit: LocatedText | None = None
    reference_range: LocatedText | None = None
    judgement: LocatedText | None = None
    confidence: float = 1.0


class RawTable(BaseModel):
    rows: list[RawTableRow] = Field(default_factory=list)
    page: int = 0
