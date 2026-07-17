"""Back-compat shim. The medical advisor now lives in the package at
`doc2rag.advisor`; this module re-exports it so existing imports keep working."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from doc2rag.advisor import (  # noqa: E402,F401
    advise,
    build_advice_markdown,
    recommend_hospitals,
    unique_departments,
)

__all__ = ["advise", "build_advice_markdown", "recommend_hospitals", "unique_departments"]


if __name__ == "__main__":
    import json

    root = Path(__file__).resolve().parent.parent
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "result.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    print(f"unique departments: {len(unique_departments())}")
    print(build_advice_markdown(doc))
