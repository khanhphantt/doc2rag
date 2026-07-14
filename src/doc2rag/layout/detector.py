from __future__ import annotations

from typing import Any

import numpy as np

from doc2rag.schema.intermediate import BBox, LayoutRegion, RegionType

# PP-DocLayout's label set includes several title-like and body-like labels;
# anything not listed here (image/formula/chart/seal/algorithm/...) falls
# back to TEXT, which is harmless since those regions carry little/no
# extractable text for a 健康診断 form.
_TITLE_LABELS = {"doc_title", "paragraph_title", "table_title", "figure_title"}


class LayoutDetector:
    """Thin wrapper around PP-StructureV3 (paddleocr>=3.x).

    Lazily loads the underlying model on first use so importing this module
    (and the rest of the package) doesn't pay PaddleOCR's model-download/init
    cost unless layout detection is actually invoked.

    PP-StructureV3 already runs its own internal OCR pass and table
    recognizer, so each returned region carries its recognized content
    directly (`LayoutRegion.content` for text/title, `.table_html` for
    tables) — no separate full-page OCR pass is needed on top of this.
    """

    def __init__(self, lang: str = "japan") -> None:
        self._lang = lang
        self._engine: Any | None = None

    def _get_engine(self) -> Any:
        if self._engine is None:
            from paddleocr import PPStructureV3

            self._engine = PPStructureV3(
                lang=self._lang,
                # Works around a CPU-only oneDNN/PIR executor bug observed
                # with paddlepaddle 3.3.1 on this stack; revisit once
                # deploying on GPU, where mkldnn doesn't apply anyway.
                enable_mkldnn=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_formula_recognition=False,
                use_seal_recognition=False,
                use_chart_recognition=False,
                # The server det/rec models OOM on this box (~14GB alloc on a
                # 7.6GB-RAM host); mobile variants give equivalent detection
                # for this document set at a fraction of the memory.
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="PP-OCRv5_mobile_rec",
            )
        return self._engine

    def detect(self, page_image: np.ndarray) -> list[LayoutRegion]:
        """Detect table/text/title regions (with content) on an RGB page image, in reading order."""
        engine = self._get_engine()
        raw_result = engine.predict(page_image)[0]

        regions = [self._to_layout_region(block) for block in raw_result["parsing_res_list"]]
        for order, region in enumerate(regions):
            region.order = order
        return regions

    @staticmethod
    def _to_layout_region(block: Any) -> LayoutRegion:
        x0, y0, x1, y1 = block.bbox
        bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)

        if block.label == "table":
            return LayoutRegion(region_type=RegionType.TABLE, bbox=bbox, order=0, table_html=block.content)

        region_type = RegionType.TITLE if block.label in _TITLE_LABELS else RegionType.TEXT
        return LayoutRegion(region_type=region_type, bbox=bbox, order=0, content=block.content)
