"""PaddleOCR-VL parsing core — the project baseline.

Public surface:
    from doc2rag.vl import VLParser, get_parser, ParseOptions, ParseResult
    from doc2rag.vl import build_interactive_html, INTERACTIVE_CSS, INTERACTIVE_HEAD
"""

from doc2rag.vl.models import Block, Page, ParseOptions, ParseResult
from doc2rag.vl.parser import VLParser, get_parser
from doc2rag.vl.render import (
    INTERACTIVE_CSS,
    INTERACTIVE_HEAD,
    build_interactive_html,
)

__all__ = [
    "Block",
    "Page",
    "ParseOptions",
    "ParseResult",
    "VLParser",
    "get_parser",
    "build_interactive_html",
    "INTERACTIVE_CSS",
    "INTERACTIVE_HEAD",
]
