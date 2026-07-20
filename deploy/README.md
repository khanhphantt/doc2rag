# Deploying the doc2rag parsing API to Modal

One Modal app serves **both** parsers behind a single FastAPI service:

| Endpoint | Engine | Needs GPU? |
|---|---|---|
| `GET /health` | — | no |
| `POST /parse` | PaddleOCR-VL (PDF / image → Markdown + layout blocks) | GPU recommended |
| `POST /parse-excel` | stacked-table detection in `.xlsx` / `.xlsm` | no (pure Python) |
| `POST /advise` | LLM medical advisor (optional) | no (needs OpenAI key) |

The service code is [`deploy/modal_app.py`](./modal_app.py); it just wraps the existing
`doc2rag.api.app` FastAPI app, so the same thing you run locally is what ships.

---

## Step 1 — Install & authenticate Modal (one time)

```bash
pip install modal
modal setup          # opens a browser to link your Modal account
```

If you don't have an account yet, `modal setup` walks you through creating one at
[modal.com](https://modal.com).

## Step 2 — (optional) Enable the `/advise` endpoint

**Skip this for now** — `/parse` and `/parse-excel` need no secret, and the app
deploys without one by default. Only do this if you want the medical advisor:

```bash
modal secret create doc2rag-openai DOC2RAG_OPENAI_API_KEY=sk-...
```

then set `ADVISOR_SECRET_NAME = "doc2rag-openai"` in `deploy/modal_app.py`.
(Leaving it `None` — the default — is what lets `modal serve` run with no secret.)

## Step 3 — Run it in dev (hot reload)

From the repo root:

```bash
modal serve deploy/modal_app.py
```

Modal builds the image (first build takes a while — it installs PaddlePaddle and
**bakes the ~1 GB PaddleOCR-VL weights** into the image) and prints a temporary URL.
Edits to the code hot-reload.

## Step 4 — Deploy the persistent service

```bash
modal deploy deploy/modal_app.py
```

You get a stable public URL like `https://<you>--doc2rag-parsers-api.modal.run`.
That is the base URL your Node.js RAG backend calls.

## Step 5 — Test it

```bash
BASE=https://<you>--doc2rag-parsers-api.modal.run

curl $BASE/health

# Excel (fast, CPU)
curl -F file=@data/excels/multi.tables.xlsx $BASE/parse-excel

# PDF / image (PaddleOCR-VL)
curl -F file=@data/健康診断.png $BASE/parse
```

From Node:

```js
const form = new FormData();
form.append("file", fileBlob, "checkup.xlsx");
const res = await fetch(`${BASE}/parse-excel`, { method: "POST", body: form });
const { tables, markdown } = await res.json();   // feed into your RAG chunker
```

---

## CPU vs GPU

`deploy/modal_app.py` defaults to **CPU** so it deploys with zero extra setup
(PaddleOCR-VL works, just ~tens of seconds/page). For production speed, edit the
config block at the top of that file:

```python
GPU = "L4"                                        # was None
PADDLE_INDEX = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"
PADDLE_WHEEL = "paddlepaddle-gpu==3.2.1"
```

The GPU wheel needs a CUDA-matched image, so **rebuild and test** (`modal serve`)
before relying on it. Excel parsing never needs the GPU — if Excel volume is high,
consider splitting it into its own CPU-only Modal function so it never waits behind
a GPU container (see `docs/SERVICES.md`).

## Cost / scaling notes

- `min_containers=0` → **scales to zero** when idle; you pay only while parsing.
- `scaledown_window=300` keeps a warm container for 5 min so bursts avoid repeated
  cold starts. Raise it during a live demo; a cold start reloads the model (~10–30 s).
- `@modal.concurrent(max_inputs=1)` runs one heavy VL parse per container; Modal adds
  containers under load. Tune per your latency/cost target.

## Version caveat

Modal occasionally renames decorators/params (e.g. `scaledown_window`,
`min_containers`, `@modal.concurrent`, `add_local_dir(..., copy=, ignore=)`). If a
build errors on an unknown argument, check the current [Modal docs](https://modal.com/docs)
and adjust — the structure (image → asgi_app wrapping `doc2rag.api.app`) stays the same.

## Data / compliance reminder

Modal is a US-based third-party platform. Fine for the demo and the test document,
but before sending **real 健康診断 patient data** confirm it meets your
privacy/residency requirements — otherwise deploy the same container to a Tokyo-region
host instead (see `docs/SERVICES.md`).
