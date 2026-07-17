# doc2rag

Parse documents (scanned PDFs or photographed images) into **Markdown + structured
JSON** with an **interactive layout view** — hover a detected region on the page and
its parsed block highlights (and vice-versa). The baseline engine is
[PaddleOCR-VL](https://aistudio.baidu.com/paddleocr) 1.6; an optional LLM
**medical advisor** flags concerning findings in a 健康診断 (health checkup) and
recommends Tokyo hospitals.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design and codemap.

## Setup

```bash
pip install -e ".[vl,dev]"
# Install a matching PaddlePaddle build for your hardware:
#   GPU (CUDA 12.6): pip install paddlepaddle-gpu==3.2.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
#   CPU:             pip install paddlepaddle==3.2.1     -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
cp .env.example .env   # set DOC2RAG_OPENAI_API_KEY for the medical advisor
```

The first parse downloads the PaddleOCR-VL 1.6 weights (~1 GB) to `~/.paddlex/`.

## Run the API

```bash
uvicorn doc2rag.api.app:app --reload
```

- `POST /parse` — multipart upload (`file` = pdf/png/jpg/…, plus an optional
  `options` JSON string matching `ParseOptions`). Returns:
  - `markdown` — the recovered document as Markdown,
  - `pages[]` — per page: `width`, `height`, `image` (data URI), and `blocks[]`
    (`id`, `order`, `label`, `content`, `bbox`),
  - `interactive_html` + `assets.css` / `assets.head_js` — a ready-to-embed
    hover-linked layout view.
- `POST /advise` — body `{"markdown": "..."}` or `{"document": {...}}`; returns
  `{"advice_markdown": "..."}` (findings → departments → Tokyo hospitals). Reference only.

## Run the interactive demo

```bash
python scripts/gradio_app_paddleocr_vl.py
```

The demo is a thin UI over the same core (`doc2rag.vl` + `doc2rag.advisor`) with
all PaddleOCR-VL settings exposed (with hover tooltips) and the advisor button.

## Library use

```python
from doc2rag.vl import get_parser, ParseOptions, build_interactive_html

result = get_parser().parse("checkup.pdf", ParseOptions(layout_analysis=True))
print(result.markdown)                 # Markdown
print(result.pages[0].blocks[0].bbox)  # structured blocks + geometry
html = build_interactive_html(result)  # interactive view (needs INTERACTIVE_CSS/HEAD)
```

## Legacy pipeline

The original Google Document AI + LLM structuring pipeline (`doc2rag.pipeline`,
`docai/`, `structuring/`, `tables/`, `validation/`, `schema/`) is retained in the
tree but is no longer wired into the API. Call it as a library
(`DocumentPipeline().process(path)` → `CanonicalDocument`); see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tests

```bash
pytest tests/test_vl_core.py     # core tests (no model weights needed)
pytest                            # full suite (legacy tests need their deps)
```
