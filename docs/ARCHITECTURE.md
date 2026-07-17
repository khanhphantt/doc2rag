# 0. Baseline: PaddleOCR-VL (current)

The project's baseline engine is **PaddleOCR-VL 1.6** (the vision-language model
behind https://aistudio.baidu.com/paddleocr). It parses a PDF/image directly into
Markdown + layout blocks — no separate OCR/table/LLM-structuring stages.

**Core package — `src/doc2rag/vl/`:**
- `models.py` — `ParseOptions` (every knob → PaddleOCR-VL `predict()` kwargs),
  and the output shape: `Block` (id/order/label/content/bbox), `Page`
  (width/height/blocks/image), `ParseResult` (markdown + pages).
- `parser.py` — `VLParser` (lazy singleton pipeline, all optional sub-modules
  loaded so options toggle per-`predict()`); `get_parser().parse(path, options)
  → ParseResult`. Multi-page PDFs go through `restructure_pages`.
- `render.py` — `build_interactive_html(result)` (hover-linked page↔block view),
  `page_images()` rasterization, and `INTERACTIVE_CSS` / `INTERACTIVE_HEAD`.

**Advisor — `src/doc2rag/advisor.py`:** LLM medical advisor + Tokyo hospital
finder over the parsed Markdown (reads `data/hospitals/*.csv`). Reference only.

**Exposed API — `src/doc2rag/api/app.py`:**
- `POST /parse` → `{markdown, pages[], interactive_html, assets{css,head_js}}`.
- `POST /advise` → `{advice_markdown}`.
- `GET /health`.

**Demo — `scripts/gradio_app_paddleocr_vl.py`:** a thin Gradio UI over the same
core, exposing all settings (with hover `?` tooltips) and the advisor.

Everything below (§1–§5) documents the **legacy** Google Document AI + LLM
structuring pipeline (`doc2rag.pipeline`, `docai/`, `structuring/`, `tables/`,
`validation/`, `schema/`). It is retained in the tree for reference but is no
longer wired into the API, and it ends at the `CanonicalDocument` — RAG
chunking/embedding has been removed (persisting to a vector store is a
downstream concern, out of scope for this repo).

---

*Table of Content*
<!-- TOC -->
* [1. Overview](#1-overview)
* [2. Pipeline](#2-pipeline)
* [3. Codemap](#3-codemap)
* [4. Invariants](#4-invariants)
* [5. Open items](#5-open-items)
<!-- TOC -->

# 1. Overview

doc2rag extracts structured, RAG-ready data from 健康診断 (health checkup) documents — scanned PDFs, photographed
images, or Excel exports — which contain multiple irregular tables (test-result grids that vary by clinic template)
plus free text (問診票 answers, 医師所見, 総合判定). Output is a canonical JSON record.

The core design choice: OCR/layout extraction (Google Document AI) produces verifiable ground-truth text plus
per-field spatial location, and an LLM (OpenAI/Gemini) is used only to *structure and normalize* that text into
JSON — never to read the raw image and invent values. This matters for two reasons: dense multi-table medical
documents are exactly the case where pure vision-LLM extraction is known to hallucinate digits (unacceptable for
health data), and a separate frontend project needs a reliable bounding box per test-result item to power a
hover-to-define UI — geometry an LLM cannot be trusted to reproduce verbatim either.

# 2. Pipeline

```
Input (PDF/image/Excel)
  -> ingestion (Excel parse, or raw file bytes for Document AI)
  -> Document AI (single call: OCR + layout + table structure, each cell/paragraph carrying
     a stable id, text, and normalized bounding-box location)
  -> table reconstruction (grid -> item/value/unit/reference/judgement rows, fuzzy-matched
     against a canonical item-name dictionary; location carried through on each cell)
  -> LLM structuring (OCR text + table rows, each row keyed by id -> canonical JSON,
     schema-constrained, cannot invent numbers; echoes back a source_row_id per result
     instead of ever handling geometry itself)
  -> location resolution (source_row_id -> real Location, looked up in an index built
     before the LLM ran; unresolvable ids are flagged as likely hallucinations)
  -> validation (cross-check LLM output against OCR ground truth + plausibility ranges; flag, never
     silently correct)
  -> CanonicalDocument (final output; the caller persists/indexes it as needed)
```

Location never passes through the LLM. Bounding boxes must be exact, so the LLM only ever sees/produces a
`source_row_id` string; `structuring/location_resolver.py` resolves that id back to the real `Location` using an
index built at extraction time, before the LLM was ever invoked. This also gives a free hallucination check: any
echoed id that isn't in the index gets flagged rather than silently trusted.

# 3. Codemap

- `src/doc2rag/ingestion/` — `loaders.py` (`detect_source_type`, `mime_type_for` — Document AI takes raw file
  bytes directly, so there is no page-rendering step here), `excel.py` (bypasses Document AI/OCR entirely,
  builds `RawTableRow`s with `location=None` since there's no visual position to report).
- `src/doc2rag/docai/` — `client.py`'s `DocAiClient` wraps
  `documentai_v1.DocumentProcessorServiceClient.process_document()`; `extract.py`'s `extract_document()` walks
  the returned `Document` proto's `pages[].tables[]` (into `LocatedText` grids, text sliced from `document.text`
  via each cell's `textAnchor`, location from `layout.boundingPoly.normalizedVertices`) and `pages[].paragraphs[]`
  (free text), plus `PageMeta` (page dimensions) so the FE can convert normalized vertices to pixels.
- `src/doc2rag/tables/reconstruct.py` — `reconstruct_table_from_grid` detects header column roles
  (item/value/unit/reference/judgement) including *repeating* column groups (health-checkup tables often pack
  2-3 metrics per physical row) from a `list[list[LocatedText]]` grid; `item_dictionary.py` fuzzy-matches OCR'd
  item names to a canonical name list (`ITEM_DICTIONARY`, currently a seed set — extend as new clinic templates
  are observed).
- `src/doc2rag/structuring/` — `client.py` defines the `StructuringClient` protocol with both an OpenAI
  implementation (`OpenAIStructuringClient`) and a Gemini implementation (`GeminiStructuringClient`), selected
  via `settings.llm_provider`. OpenAI uses `response_schema.py`'s hand-written strict-mode JSON Schema
  (deliberately not derived from the Pydantic model, since OpenAI's strict mode has stricter constraints than
  Pydantic's default schema output); Gemini instead passes `llm_output_schema.py`'s `LlmStructuredOutput`
  Pydantic model directly as `response_schema`. Both schemas include a nullable `source_row_id` per result.
  `prompts.py` builds the prompt (each raw row prefixed with `id:...`) and carries the "never invent a number"
  and "echo the source row id" instructions. `location_resolver.py` resolves `source_row_id` back to a real
  `Location` post-hoc (see Pipeline above) — it reads the raw LLM output dict directly, since `TestResult` itself
  has no `source_row_id` field (pydantic drops unknown kwargs silently, so this must happen before that point).
- `src/doc2rag/schema/canonical.py` — `CanonicalDocument` and friends: the final output shape. `TestResult.location`
  carries the item's bounding box; `CanonicalDocument.pages` carries per-page `PageMeta` (dimensions).
- `src/doc2rag/schema/intermediate.py` — pipeline-internal types: `Location`/`NormalizedVertex` (Document AI's
  normalized 0-1 polygon convention), `LocatedText` (id + text + optional location — the unit everything is built
  from), `RawTable`/`RawTableRow`.
- `src/doc2rag/validation/rules.py` — `validate_document`: flags (never silently fixes) LLM output that
  disagrees with OCR ground truth or falls outside plausibility ranges (`PLAUSIBILITY_RANGES`).
- `src/doc2rag/pipeline.py` — `DocumentPipeline`, wires every stage above into one `.process(path)` call that
  returns a `CanonicalDocument`.
- `src/doc2rag/api/app.py` — FastAPI app for the PaddleOCR-VL baseline (`POST /parse`, `POST /advise`,
  `GET /health`). The legacy `DocumentPipeline` is **not** exposed here; call it as a library.
- `scripts/check_api_keys.py` — standalone script that makes one cheap list-models call per provider to verify
  `DOC2RAG_OPENAI_API_KEY`/`DOC2RAG_GEMINI_API_KEY` in `.env` are valid, without running the extraction pipeline.

# 4. Invariants

- **The LLM structuring step never receives the raw image as its primary input** — only OCR text and
  reconstructed table rows. It cannot introduce a numeric value that isn't traceable to OCR output; this is
  enforced by prompt instruction (`structuring/prompts.py`) and checked post-hoc in `validation/rules.py`.
- **The LLM never sees or produces geometry.** It only echoes a `source_row_id`; the real `Location` is resolved
  deterministically by our own code (`structuring/location_resolver.py`) against an id→location index built
  before the LLM ran. An id that doesn't resolve is flagged, never guessed.
- **Validation never silently corrects a value.** A mismatch or implausible value only ever sets
  `needs_review=True` and appends a flag to `processing_meta.flags` — human review is the only path to
  overriding a flagged field.
- **Excel input bypasses Document AI/OCR/LLM-vision entirely** (`ingestion/excel.py` -> `RawTable` directly, with
  `location=None`) but still passes through the same LLM-structuring/validation stages as scanned input,
  so downstream consumers see one consistent schema regardless of source type.

# 5. Open items

1. `ITEM_DICTIONARY` in `tables/item_dictionary.py` is a seed set; extend it as real clinic templates are
   observed.
2. LLM call volume/cost ceiling per document is not yet bounded — currently every document gets one full
   structuring call.
3. Original file + canonical JSON archival location (S3/GCS/local) is not yet implemented.
4. `TestResult`/canonical schema stores one value per item. Some real clinic templates (confirmed via a sample
   健康診断個人票 form) report up to three time points per item (今回/前回/前々回 — current/previous/two-visits-ago)
   in the same table. Current behavior: the LLM structuring prompt is only given the raw table rows/OCR text
   and asked to produce the schema as defined, so multi-column history collapses to whatever the model picks
   (observed: 今回/current). To answer trend questions ("has my blood sugar improved?"), the schema needs a
   `history` field per result rather than a single `value`.
5. The structuring step can silently drop reconstructed rows (observed: the 肝炎 / その他 blood items were
   reconstructed but omitted from the canonical output). Validation only checks items the LLM *did* emit, so a
   per-section completeness check (canonical count vs. reconstructed-row count) would catch these drops.
6. Document AI table parsing on dense multi-table scans still merges reference-range/unit/value into single
   cells (see the blood grid). The header-role detector then finds no clean header and falls back to the
   item-name heuristic; pre-splitting cells on the embedded 基準値/単位 pattern before the LLM sees them would
   improve recall.

Verified end-to-end (2026-07): Document AI is provisioned (`DOC2RAG_GCP_*` + `GOOGLE_APPLICATION_CREDENTIALS`),
and `DocumentPipeline` runs against `data/健康診断.png` producing a `CanonicalDocument` with per-item
`Location`s. `scripts/run_visualize.py` renders every stage (extraction / reconstruction / located items) as
JSON + bounding-box overlays into `data/output/` for visual sanity-checking.
