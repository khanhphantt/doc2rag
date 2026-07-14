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
plus free text (問診票 answers, 医師所見, 総合判定). Output is a canonical JSON record plus a set of per-section text
chunks with embeddings, written to MongoDB for retrieval by the existing RAG chatbot.

The core design choice: layout detection + OCR (PaddleStructure/PaddleOCR) produces verifiable ground-truth text,
and an LLM (OpenAI/Gemini) is used only to *structure and normalize* that text into JSON — never to read the raw
image and invent values. This matters because dense multi-table medical documents are exactly the case where
pure vision-LLM extraction is known to hallucinate digits, which is unacceptable for health data.

# 2. Pipeline

```
Input (PDF/image/Excel)
  -> ingestion (page render / Excel parse)
  -> preprocessing (deskew/denoise, OpenCV)
  -> layout detection + OCR + table recognition in one pass (PP-StructureV3: table/text/title
     regions + reading order + recognized content, per region)
  -> table reconstruction (HTML grid -> item/value/unit/reference/judgement rows, fuzzy-matched
     against a canonical item-name dictionary)
  -> LLM structuring (OCR text + table rows -> canonical JSON, schema-constrained, cannot invent numbers)
  -> validation (cross-check LLM output against OCR ground truth + plausibility ranges; flag, never
     silently correct)
  -> chunking (one chunk per section + one summary chunk, with patient/date/facility metadata)
  -> embedding + MongoDB write
```

Note: PP-StructureV3 (paddleocr>=3.x) runs its own internal OCR pass and table recognizer as part of
layout parsing, so `LayoutDetector` returns each region already carrying its recognized text
(`LayoutRegion.content`) or table HTML (`.table_html`) — there is no separate full-page OCR pass on top
of it. `OcrEngine` (PaddleOCR) is kept as a standalone re-reader for a not-yet-wired low-confidence-cell
fallback path (see open items), not as the primary per-region reader.

See the full stage-by-stage rationale in the original design discussion; this file tracks the codemap and
invariants that are expensive to rediscover from source.

# 3. Codemap

- `src/doc2rag/ingestion/` — PDF/image page loading (`loaders.py`), OpenCV preprocessing (`preprocess.py`),
  Excel table parsing (`excel.py`, bypasses OCR entirely).
- `src/doc2rag/layout/detector.py` — `LayoutDetector`, wraps `PPStructureV3` (paddleocr>=3.x; the class was
  renamed and its API rewritten from the 2.x `PPStructure`/`show_log=`/callable-object style to
  `PPStructureV3(...).predict(image)`). Lazily loads the model so importing the package doesn't pay init cost
  until layout detection actually runs. Disables the formula/seal/chart sub-pipelines (`use_formula_recognition
  =False` etc.) since 健康診断 forms never need them — this alone cuts a large chunk of init time/memory, since
  PP-StructureV3 otherwise loads ~11 separate models by default.
- `src/doc2rag/ocr/engine.py` — `OcrEngine`, wraps `PaddleOCR` (paddleocr>=3.x: `.predict()` returning
  `rec_texts`/`rec_scores`/`rec_boxes`, not the 2.x `.ocr(cls=True)` nested-list format). Standalone low-
  confidence-fallback reader, not called from the main pipeline yet (see open items).
- `src/doc2rag/tables/` — `html_grid.py` parses PP-Structure's table HTML into a rectangular cell grid;
  `reconstruct.py` detects header column roles (item/value/unit/reference/judgement) including *repeating*
  column groups (health-checkup tables often pack 2-3 metrics per physical row); `item_dictionary.py` fuzzy-
  matches OCR'd item names to a canonical name list (`ITEM_DICTIONARY`, currently a seed set — extend as new
  clinic templates are observed).
- `src/doc2rag/structuring/` — `client.py` defines the `StructuringClient` protocol with both an OpenAI
  implementation (`OpenAIStructuringClient`) and a Gemini implementation (`GeminiStructuringClient`), selected
  via `settings.llm_provider`. OpenAI uses `response_schema.py`'s hand-written strict-mode JSON Schema
  (deliberately not derived from the Pydantic model, since OpenAI's strict mode has stricter constraints than
  Pydantic's default schema output); Gemini instead passes `llm_output_schema.py`'s `LlmStructuredOutput`
  Pydantic model directly as `response_schema` (Gemini's SDK supports this natively, no hand-written JSON
  Schema needed). Both produce the same dict shape consumed by `pipeline.py`'s `_to_canonical_document`.
  `prompts.py` builds the prompt and carries the "never invent a number" instruction.
- `src/doc2rag/schema/canonical.py` — `CanonicalDocument` and friends: the final output shape.
- `src/doc2rag/schema/intermediate.py` — pipeline-internal types (`LayoutRegion`, `OcrRegionResult`, `RawTable`).
- `src/doc2rag/validation/rules.py` — `validate_document`: flags (never silently fixes) LLM output that
  disagrees with OCR ground truth or falls outside plausibility ranges (`PLAUSIBILITY_RANGES`).
- `src/doc2rag/chunking/` — `chunker.py` builds one `Chunk` per section plus a summary chunk; `embed.py` embeds
  chunk text via OpenAI or Gemini's embedding API, following the same `settings.llm_provider` switch as
  structuring (so one setting change covers both without needing two valid provider keys at once).
- `src/doc2rag/storage/mongo.py` — `MongoChunkStore`, writes chunks to MongoDB. Does not manage the vector
  index itself (see open items).
- `src/doc2rag/pipeline.py` — `DocumentPipeline`, wires every stage above into one `.process(path)` call.
- `src/doc2rag/api/app.py` — FastAPI app, single `POST /process` endpoint (near-real-time, synchronous).
- `scripts/check_api_keys.py` — standalone script that makes one cheap list-models call per provider to verify
  `DOC2RAG_OPENAI_API_KEY`/`DOC2RAG_GEMINI_API_KEY` in `.env` are valid, without running the OCR pipeline. Run
  this before a full pipeline test to catch a bad key in seconds instead of after several minutes of OCR.

# 4. Invariants

- **The LLM structuring step never receives the raw image as its primary input** — only OCR text and
  reconstructed table rows. It cannot introduce a numeric value that isn't traceable to OCR output; this is
  enforced by prompt instruction (`structuring/prompts.py`) and checked post-hoc in `validation/rules.py`.
- **Validation never silently corrects a value.** A mismatch or implausible value only ever sets
  `needs_review=True` and appends a flag to `processing_meta.flags` — human review is the only path to
  overriding a flagged field.
- **Excel input bypasses OCR/layout/LLM-vision entirely** (`ingestion/excel.py` -> `RawTable` directly) but
  still passes through the same LLM-structuring/validation/chunking stages as scanned input, so downstream
  consumers see one consistent schema regardless of source type.

# 5. Open items

1. Confirm the embedding model + index config (dimension, distance metric) the existing MongoDB Atlas Vector
   Search setup expects — currently defaults to `text-embedding-3-small` (see `config.py`).
2. `ITEM_DICTIONARY` in `tables/item_dictionary.py` is a seed set; extend it as real clinic templates are
   observed.
3. LLM call volume/cost ceiling per document is not yet bounded — currently every document gets one full
   structuring call.
4. Original file + canonical JSON archival location (S3/GCS/local) is not yet implemented.
5. ~~`GeminiStructuringClient` is a stub~~ — implemented; both OpenAI and Gemini structuring/embedding are now
   live (see codemap). Not yet exercised end-to-end against a real document (see item 10).
6. `TestResult`/canonical schema stores one value per item. Some real clinic templates (confirmed via a sample
   健康診断個人票 form) report up to three time points per item (今回/前回/前々回 — current/previous/two-visits-ago)
   in the same table. Current behavior: the LLM structuring prompt is only given the raw table rows/OCR text
   and asked to produce the schema as defined, so multi-column history is expected to collapse to whatever the
   model picks (likely 今回/current) — this hasn't been verified against a real LLM response yet. If the RAG
   chatbot needs to answer trend questions ("has my blood sugar improved?"), the schema needs a `history` field
   per result rather than a single `value`.
7. **PP-StructureV3 is heavy and CPU inference is not near-real-time.** Confirmed by direct testing on a
   CPU-only dev sandbox (no GPU, oneDNN disabled due to a paddlepaddle 3.3.1 CPU bug, see below): a 450x708px
   crop alone took ~20s model init + ~74s predict; a full ~2000x1400px scanned page would run well past the
   10-30s near-real-time target from this design's original constraints. Peak process memory observed around
   5-6GB against a 7.6GB box. **Production deployment needs a GPU** (or a cloud OCR/layout API instead of
   self-hosted PaddleOCR) to hit the near-real-time SLA — this was explicitly out of scope to fix on the dev
   sandbox (target deployment is GPU-backed) but must be validated on real target hardware before launch.
8. `paddleocr` does not declare `paddlepaddle` (the ML framework) or the `paddlex[ocr]` extras (layout/table
   sub-models) as installable dependencies — both had to be added explicitly to `pyproject.toml`. A fresh
   `pip install -e .` should now pull them in, but this is worth double-checking on the target deployment
   environment (GPU builds of `paddlepaddle` use a different install command/index than the CPU wheel from
   PyPI — see PaddlePaddle's install docs for the CUDA version in use).
9. On this dev sandbox, PaddleOCR/PP-StructureV3 needed `enable_mkldnn=False` to avoid a
   `NotImplementedError` from paddlepaddle 3.3.1's oneDNN PIR executor
   (`ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`) on CPU
   inference. This flag is hardcoded off in `layout/detector.py`/`ocr/engine.py`; revisit once running on the
   real GPU target, where this CPU-specific backend doesn't apply anyway.
10. **Full-page processing crashed outright with an out-of-memory error** on this dev sandbox: PaddleOCR's text
    detector tried to allocate ~14.7GB for one ~2000x1400px page (`ResourceExhaustedError`), and even a small
    cropped table region (~320x710px) intermittently pushed this 7.6GB-RAM box into full swap exhaustion and
    thrashing on repeated back-to-back runs (two earlier runs on the identical crop completed fine; a third
    attempt right after did not and was killed after 12+ minutes with no progress). This is a genuine resource-
    sizing concern, not a code bug — confirm the target GPU deployment has enough VRAM/host RAM before assuming
    the "near-real-time" SLA holds, and consider capping the detector's internal working resolution
    (`text_det_limit_side_len`, see item 7) as a safety net regardless of hardware.
11. **The full pipeline (OCR/layout/table → LLM structuring → validation → chunking → embedding) has not yet
    been observed completing end-to-end against a real document.** What *is* confirmed working, each verified
    independently against a real cropped 健康診断個人票 table (肥満・視聴覚器官のチェック, including its
    今回/前回/前々回 multi-column structure):
    - Layout detection + OCR + table HTML extraction via `PPStructureV3` (succeeded twice on the same crop)
    - Table reconstruction into item/value/unit/reference/judgement rows (unit-tested, not yet observed on
      this specific table's repeating-column layout in a live run)
    - Gemini API connectivity (key verified valid via `scripts/check_api_keys.py`) and OpenAI embedding API
      calls (from earlier, pre-Gemini test runs)
    What's *not yet* confirmed: a full run reaching `GeminiStructuringClient.structure()` and producing a
    parsed `CanonicalDocument` — every attempt was blocked by something external to the pipeline logic itself
    (an invalid OpenAI key, then sandbox memory thrashing on retry with Gemini). Before considering this
    pipeline production-ready, run it end-to-end on a machine with adequate RAM/GPU and inspect: whether the
    LLM's JSON validates against `LlmStructuredOutput`, how it handles the 今回/前回/前々回 columns (see item 6),
    and whether `validation.py`'s flags fire sensibly against real OCR/LLM output (validated only with
    synthetic data in `tests/test_validation.py` so far).
