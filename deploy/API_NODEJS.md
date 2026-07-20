# doc2rag parsing API — Node.js client guide

Base URL: `https://khanh-phan--doc2rag-parsers-api.modal.run`

```js
const BASE = "https://khanh-phan--doc2rag-parsers-api.modal.run";
```

The service scales to zero when idle, so the **first request after a quiet period
cold-starts the model (~10–30 s)**. Warm requests are fast. Set a generous client
timeout (60 s+) for `/parse`.

---

## Interactive docs (Swagger)

Fastest way to explore/test in the browser — no code needed:

| URL | What |
|---|---|
| [`/docs`](https://khanh-phan--doc2rag-parsers-api.modal.run/docs) | **Swagger UI** — "Try it out" to upload a file and fire requests live |
| [`/redoc`](https://khanh-phan--doc2rag-parsers-api.modal.run/redoc) | ReDoc — clean read-only reference |
| [`/openapi.json`](https://khanh-phan--doc2rag-parsers-api.modal.run/openapi.json) | OpenAPI 3 spec — feed to codegen / Postman / Insomnia |

Open `/docs`, expand **POST /parse**, click *Try it out*, choose a PDF/image, and
Execute — you'll see the exact response before writing any Node code.

---

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET`  | `/health` | — | `{ "status": "ok" }` |
| `POST` | `/parse`  | `multipart/form-data` (a PDF or image file) | Markdown + layout blocks + interactive HTML |
| `POST` | `/advise` | `application/json` | Medical-advisor Markdown |

Supported `/parse` file types: `.pdf`, `.png`, `.jpg`/`.jpeg`, and other common images.

---

## `POST /parse`

Multipart form fields:

| Field | Type | Default | Notes |
|---|---|---|---|
| `file` | file | — | **required** — the PDF/image to parse |
| `options` | string (JSON) | `"{}"` | parser knobs; leave empty for defaults |
| `include_images` | bool | `true` | embed page background images as data URIs in each page |
| `include_html` | bool | `true` | include ready-to-embed `interactive_html` + `assets` |

### Response shape

```jsonc
{
  "markdown": "# ...",           // full document as Markdown
  "model_version": "v1.6",
  "num_blocks": 42,
  "pages": [
    {
      "index": 0,                // 0-based page number
      "width": 1654.0,
      "height": 2339.0,
      "blocks": [
        {
          "id": 0,               // stable per-page index
          "order": 1,            // reading order (may be null)
          "label": "text",       // text | table | doc_title | image | ...
          "content": "…",        // plain text, or HTML string for tables
          "bbox": [x0, y0, x1, y1]  // pixels in page coords
        }
      ],
      "image": "data:image/png;base64,…"  // present when include_images=true
    }
  ],
  "interactive_html": "<div>…</div>",     // present when include_html=true
  "assets": { "css": "…", "head_js": "…" } // present when include_html=true
}
```

For RAG, the two fields you usually want are **`markdown`** (feed to your chunker)
and **`pages[].blocks[]`** (structured regions with bounding boxes).

### Node.js (Node 18+, built-in `fetch`/`FormData`/`Blob`)

```js
import fs from "node:fs/promises";

const BASE = "https://<owner>--doc2rag-parsers-api.modal.run";

async function parse(filePath, filename) {
  const buf = await fs.readFile(filePath);

  const form = new FormData();
  form.append("file", new Blob([buf]), filename);
  // optional: skip the heavy HTML/images if you only need markdown + blocks
  form.append("include_html", "false");
  form.append("include_images", "false");
  // optional parser knobs (JSON string):
  // form.append("options", JSON.stringify({ chart_recognition: true }));

  const res = await fetch(`${BASE}/parse`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`parse failed: ${res.status} ${await res.text()}`);

  const { markdown, pages, num_blocks } = await res.json();
  return { markdown, pages, num_blocks };
}

const out = await parse("./checkup.pdf", "checkup.pdf");
console.log(out.markdown.slice(0, 500));
```

> Note: `FormData`, `Blob`, and `fetch` are global in Node 18+. If you're on an
> older Node or prefer axios/`form-data`, use that library's multipart helper — the
> field names (`file`, `options`, `include_html`, `include_images`) are the same.

---

## `POST /advise`  (optional)

JSON body — send either the parsed `markdown` or a `document` object:

```js
const res = await fetch(`${BASE}/advise`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ markdown: out.markdown }),
});
const { advice_markdown } = await res.json();
```

> `/advise` is only available if the server was deployed with the OpenAI secret
> enabled. If it's not enabled you'll get an error — check with the API owner.

---

## Quick test (curl)

```bash
BASE=https://<owner>--doc2rag-parsers-api.modal.run

curl $BASE/health
# {"status":"ok"}

curl -F file=@checkup.pdf "$BASE/parse?"        # add -F include_html=false to trim output
```

## Error handling

| Status | Meaning |
|---|---|
| `400` | Unsupported file type, or invalid `options` JSON |
| `200` | Success — parse the JSON body |

Non-200 responses carry a JSON `{ "detail": "…" }` message; read `res.text()` on failure.
