# doc2rag

Extracts structured, RAG-ready JSON from 健康診断 (health checkup) documents — scanned PDFs, photographed
images, or Excel exports — that contain multiple irregular tables and free text. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full pipeline design and codemap.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env  # fill in API keys / Mongo URI
```

## Run the API

```bash
uvicorn doc2rag.api.app:app --reload
```

`POST /process` with a multipart file upload (`pdf`, `png`/`jpg`, or `xlsx`) returns the canonical JSON record,
a `needs_review` flag, and the number of chunks written to MongoDB.

## Tests

```bash
pytest
```
