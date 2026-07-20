"""Deploy the doc2rag parsing API to Modal.

Exposes ONE FastAPI app (`doc2rag.api.app`) with both engines:

    GET  /health       liveness
    POST /parse        PaddleOCR-VL: PDF/image -> Markdown + layout blocks
    POST /parse-excel  stacked-table detection in .xlsx/.xlsm  (CPU, no weights)
    POST /advise       LLM medical advisor (optional; needs OPENAI key secret)

Quickstart:
    pip install modal
    modal setup                       # one-time browser auth
    modal serve deploy/modal_app.py   # hot-reload dev URL
    modal deploy deploy/modal_app.py  # persistent public URL

See deploy/README.md for the full walkthrough (secrets, GPU, testing).

------------------------------------------------------------------------------
CPU vs GPU
------------------------------------------------------------------------------
Defaults to **CPU** so it deploys out-of-the-box (PaddleOCR-VL runs, just slower:
~tens of seconds/page). For production speed switch to GPU: set GPU = "L4" below
and flip PADDLE_WHEEL to the GPU index (see the two marked lines). The GPU wheel
needs a CUDA-matched image, so validate the build before relying on it.
"""

from __future__ import annotations

import modal

# ---- configuration -----------------------------------------------------------
APP_NAME = "doc2rag-parsers"
GPU: str | None = None          # None = CPU. For production: GPU = "L4"
SCALEDOWN_WINDOW = 300          # seconds a warm container lingers before scaling to 0
TIMEOUT = 600                   # per-request hard cap (scanned PDFs can be slow on CPU)

# Only needed for POST /advise. Leave as None to deploy WITHOUT the advisor (the
# /parse and /parse-excel endpoints don't need any secret). To enable /advise:
#   1. modal secret create doc2rag-openai DOC2RAG_OPENAI_API_KEY=sk-...
#   2. set ADVISOR_SECRET_NAME = "doc2rag-openai" below
# (Secret.from_name is lazy, so a missing secret only errors at serve/deploy time
# — hence this explicit opt-in rather than a try/except.)
ADVISOR_SECRET_NAME: str | None = None

# CPU PaddlePaddle wheel index. For GPU (CUDA 12.6) use:
#   "https://www.paddlepaddle.org.cn/packages/stable/cu126/" + "paddlepaddle-gpu==3.2.1"
PADDLE_INDEX = "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
PADDLE_WHEEL = "paddlepaddle==3.2.1"

# ---- image -------------------------------------------------------------------
# Build order matters: install deps, copy the repo, `pip install -e`, then run a
# throwaway parse so the ~1 GB PaddleOCR-VL weights are BAKED into the image
# (otherwise the first real request cold-downloads them and may time out).
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0", "libgomp1")  # OpenCV / Paddle runtime libs
    .pip_install(PADDLE_WHEEL, extra_index_url=PADDLE_INDEX)
    .add_local_dir(
        ".",
        remote_path="/root/doc2rag",
        copy=True,  # copy so the pip-install build step below can see the files
        ignore=[".venv", ".git", "data/output", "**/__pycache__", "*.pyc"],
    )
    .run_commands(
        "cd /root/doc2rag && pip install -e '.[vl]'",
        # bake the VL model weights (parses the bundled sample once)
        "cd /root/doc2rag && python -c "
        "\"from doc2rag.vl import get_parser; get_parser().parse('data/健康診断.png')\"",
    )
)

app = modal.App(APP_NAME)

_secrets = [modal.Secret.from_name(ADVISOR_SECRET_NAME)] if ADVISOR_SECRET_NAME else []


@app.function(
    image=image,
    gpu=GPU,
    secrets=_secrets,
    scaledown_window=SCALEDOWN_WINDOW,
    timeout=TIMEOUT,
    min_containers=0,  # scale to zero when idle (no standing GPU/CPU cost)
)
@modal.concurrent(max_inputs=1)  # one heavy VL parse per container at a time
@modal.asgi_app()
def api():
    # Imported inside the container (where doc2rag is installed), not at deploy time.
    from doc2rag.api.app import app as fastapi_app

    return fastapi_app
