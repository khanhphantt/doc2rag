from __future__ import annotations

from typing import Any

import numpy as np

from doc2rag.schema.intermediate import BBox, OcrLine


class OcrEngine:
    """Thin wrapper around PaddleOCR (paddleocr>=3.x), used as the targeted
    re-reader for individual crops flagged low-confidence by LayoutDetector's
    built-in recognition — not as the primary per-page reader (PP-StructureV3
    already OCRs text/title regions itself, see layout/detector.py).
    """

    def __init__(self, lang: str = "japan") -> None:
        self._lang = lang
        self._engine: Any | None = None

    def _get_engine(self) -> Any:
        if self._engine is None:
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(lang=self._lang, enable_mkldnn=False)
        return self._engine

    def read_crop(self, crop: np.ndarray) -> list[OcrLine]:
        engine = self._get_engine()
        result = engine.predict(crop)[0]

        lines: list[OcrLine] = []
        for text, score, box in zip(result["rec_texts"], result["rec_scores"], result["rec_boxes"]):
            x0, y0, x1, y1 = box
            lines.append(OcrLine(text=text, confidence=float(score), bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1)))
        return lines
