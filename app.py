"""Hugging Face Space entry point for the doc2rag PaddleOCR-VL demo.

HF Spaces (Gradio SDK) runs this file. It just wires up the existing demo:
the parse of the bundled example and its medical advice are pre-cached under
data/output/, so the startup screen shows results instantly with NO API key —
which is why this Space needs no LLM secret.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from doc2rag.vl import INTERACTIVE_CSS, INTERACTIVE_HEAD  # noqa: E402
from gradio_app_paddleocr_vl import build_demo  # noqa: E402

demo = build_demo()

if __name__ == "__main__":
    demo.launch(css=INTERACTIVE_CSS, head=INTERACTIVE_HEAD)
