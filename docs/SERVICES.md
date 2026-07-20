# doc2rag as a parsing microservice (for a Node.js RAG chatbot)

Design plan for turning the three document parsers into production services that a
Node.js RAG backend calls during document ingestion. **Plan only — no code yet.**

*Table of Content*
<!-- TOC -->
* [1. Where we are today](#1-where-we-are-today)
* [2. Target architecture](#2-target-architecture)
* [3. The unified output contract](#3-the-unified-output-contract)
* [4. Async job lifecycle](#4-async-job-lifecycle)
* [5. Routing by document type](#5-routing-by-document-type)
* [6. Production concerns](#6-production-concerns)
* [7. Roadmap](#7-roadmap)
* [8. Open decisions](#8-open-decisions)
<!-- TOC -->

## 1. Where we are today

Three parsers exist, each with a very different dependency and resource profile:

| Parser | Engine | Deps | Resource | Logic currently lives in |
|---|---|---|---|---|
| Excel (stacked tables) | connected-components over cells | `openpyxl` only | CPU, fast, tiny | `scripts/gradio_excel_tables.py` (`parse_excel()` + ~40 helpers) |
| Native PDF (tables) | Docling / TableFormer | `docling` (PyTorch) | GPU-preferred, ~s/page | `scripts/gradio_pdf_tables.py` (`parse_pdf()` + helpers) |
| Scanned / image | PaddleOCR-VL | `paddlepaddle` | GPU, ~1 GB weights | `doc2rag.vl` package (Gradio is a thin UI) ✅ |

Three structural problems to solve before any of this is a service:

1. **The Excel and PDF logic is trapped inside Gradio scripts** — not importable, not
   testable, not servable. Only the VL engine is packaged.
2. **Each demo emits its own JSON shape.** The RAG side must not care which engine ran —
   we need one output contract (§3).
3. **The two heavy engines have conflicting stacks:** Docling pulls **PyTorch**,
   PaddleOCR-VL pulls **PaddlePaddle**. Co-installing them in one image/process is fat and
   fragile, and both want GPU memory. `docling` is not in `pyproject.toml` yet.

Chosen constraints (from review): **production** target, **async job + webhook** invocation.
Those two choices essentially fix the topology in §2.

## 2. Target architecture

```
                        ┌─────────────────────────────────────────────┐
 Node.js RAG      POST  │  parser-gateway  (FastAPI, CPU, stateless)   │
 chatbot  ───────────►  │   • auth, validate, store upload → object    │
     ▲                  │     store, enqueue job, return 202 {job_id}  │
     │  webhook         │   • Excel handled INLINE (pure-python, light) │
     │  (job done)      └───────┬───────────────┬──────────────────────┘
     │                          │ queue (Redis) │  job state (Redis/PG)
     │                  ┌───────▼──────┐  ┌──────▼───────┐
     └──────────────────┤ parser-pdf   │  │ parser-image │   each: 1 GPU,
        (gateway fans    │ Docling/torch│  │ PaddleOCR-VL │   own image,
         the callback)   │ GPU worker   │  │ paddle GPU   │   scale by replicas
                         └──────────────┘  └──────────────┘
```

Node talks to **one** service (the gateway). Everything behind it is an internal concern.

**Services**
- **`parser-gateway`** (FastAPI, CPU, stateless, horizontally scalable): the only surface
  Node sees. Authenticates, validates and stores the upload, enqueues a job, returns a
  `job_id`, and delivers the completion webhook. Handles **Excel inline** (pure-python and
  light — no reason to pay a queue hop for it).
- **`parser-pdf`** (Docling / PyTorch, GPU worker): consumes PDF jobs from the queue.
- **`parser-image`** (PaddleOCR-VL / PaddlePaddle, GPU worker): consumes image / scanned
  jobs from the queue.

Separate GPU worker images keep the torch and paddle stacks from colliding and let each
scale, warm, and be replaced independently.

## 3. The unified output contract

One schema every engine normalizes to — proposed `src/doc2rag/schema/parsed.py`:

```
ParsedDocument {
  document_id, source_type: excel|pdf|image, engine, engine_version,
  markdown: str,
  tables: [ { id, title?, page?, bbox?, headers[], rows[][],
              records: [ {header: value} ] } ],
  pages:  [ { number, width, height, image_uri? } ],   # provenance for pdf/image
  metadata: { filename, page_count, warnings[] }
}
```

The RAG side (Node) chunks from `tables[].records` + `markdown`, then embeds and indexes.
**Parsing services never chunk or embed** — that seam is exactly the boundary already
enforced by removing chunking/embedding from this repo (see `ARCHITECTURE.md` §0).

## 4. Async job lifecycle

| Step | Endpoint / action | Returns |
|---|---|---|
| Submit | `POST /parse` (multipart file + `callback_url`) | `202 {job_id, status:"queued"}` |
| Poll (fallback) | `GET /jobs/{job_id}` | `{status, result?, error?}` |
| Fetch result | `GET /jobs/{job_id}/result` | `ParsedDocument` (or 404 until done) |
| Done | gateway `POST`s to `callback_url` | `{job_id, status:"succeeded", result }` or `{status:"failed", error}` |

- **States:** `queued → running → succeeded | failed`.
- **Idempotency:** accept an `Idempotency-Key` (hash of the file bytes) so a retried upload
  returns the existing job instead of re-parsing.
- **Webhook trust:** sign the callback with an HMAC header so Node can verify origin.
- **Webhook reliability:** retry with backoff; because the result is also persisted, a
  missed webhook is always recoverable via `GET /jobs/{id}/result` (poll fallback).
- **Result storage:** write `ParsedDocument` JSON to an object store (S3/GCS/MinIO). The
  webhook carries the JSON **inline** for small docs or a **URL** for large ones (decide the
  threshold — see §8).

## 5. Routing by document type

Gateway dispatches on MIME / extension:

- `.xlsx` / `.xls` → inline Excel handler.
- `.pdf` (native) → `parser-pdf` queue.
- `.png` / `.jpg` / `.tiff`, and scanned PDFs → `parser-image` queue.

**Native vs scanned PDF:** try Docling's text layer first; if a page has no extractable
text, fall back to the image engine. Expose a `force_engine` override for callers that
already know.

## 6. Production concerns

- **Model lifecycle:** load weights once at worker startup (the VL parser already does this
  via a singleton); keep workers warm; the readiness probe passes only after weights load.
  GPU workers run concurrency 1–2 and scale by replica count, not threads.
- **Sizing (volume unknown):** start each GPU worker at 1 replica; the queue absorbs bursts;
  autoscale replicas on **queue depth**. This is the core reason for async — a spike queues
  instead of timing out.
- **Timeouts / dead-letter:** per-job hard timeout; failed jobs go to a dead-letter queue
  and emit a `failed` webhook — never a silent hang.
- **Security:** authenticate the gateway (API key / mTLS from Node); cap upload size;
  validate MIME by content, not just extension; sandbox parsing.
- **Observability:** structured logs keyed by `job_id`; per-engine queue-depth and
  parse-latency metrics; `/health` (liveness) + `/ready` (weights loaded) on every service.

## 7. Roadmap

1. **Prerequisite refactor** *(required regardless of topology)* — extract `parse_excel()` /
   `parse_pdf()` out of the Gradio scripts into `doc2rag/excel/` and `doc2rag/pdf/`; add the
   `ParsedDocument` schema (§3) + one adapter per engine; add a `pdf` extra (`docling`) to
   `pyproject.toml`. The Gradio files become thin UIs (like the VL demo). Add unit tests
   around the extracted logic.
2. **Gateway MVP** — `POST /parse` + `GET /jobs/{id}`, Redis queue, in-process worker,
   synchronous webhook, Excel inline. Ship one engine end-to-end.
3. **Split GPU workers** — move PDF and image parsing into their own images/deployments
   consuming the queue; the gateway only routes and owns webhooks.
4. **Harden** — idempotency, webhook signing + retries, dead-letter, autoscale on queue
   depth, and OpenAPI → generated TypeScript client for Node.

## 8. Open decisions

- **Webhook payload:** result **inline vs URL** (and the size threshold). Affects the Node
  contract and object-store setup — decide before wiring step 2.
- **Job store:** Redis-only (simple, ephemeral) vs Redis queue + Postgres for durable job
  history/audit (better for production traceability).
- **Native-vs-scanned PDF detection:** automatic text-layer probe vs always require the
  caller to pass `force_engine`.
- **Deployment substrate:** Kubernetes (GPU node pool + HPA on queue depth) vs a simpler
  single-host Docker Compose to start.
