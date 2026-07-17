*Table of Content*
<!-- TOC -->
* [1. Getting Started](#1-getting-started)
* [2. Internal resources and communication channels](#2-internal-resources-and-communication-channels)
* [3. Setting up the environment](#3-setting-up-the-environment)
<!-- TOC -->

# 1. Getting Started
To get started contributing to this project, you can follow the checklist below:
- [ ] Make sure you have access to the [internal resources and communication channels](#2-internal-resources-and-communication-channels)
- [ ] [Setup the development environment](#3-setting-up-the-environment)
- [ ] Read the [contributing guidelines](./CONTRIBUTING.md)
- [ ] Read the [architecture](./ARCHITECTURE.md) document

# 2. Internal resources and communication channels

- **Code & issues** — this GitHub repository (source, issue tracker, pull requests).
- **Architecture & design** — [ARCHITECTURE.md](./ARCHITECTURE.md): the PaddleOCR-VL baseline
  (`src/doc2rag/vl/`, the `/parse` API, the interactive layout view) and the retained legacy
  Document AI + LLM structuring pipeline.
- **Contributing** — [CONTRIBUTING.md](./CONTRIBUTING.md): code style, docstrings, branch naming, PR flow.

[//]: # (TODO: add team-specific chat/ticketing links once the project has them.)

# 3. Setting up the environment

Requires Python ≥ 3.10.

```bash
# 1. Clone and create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install the package. Extras:
#    vl  -> PaddleOCR-VL baseline engine + Gradio demo
#    dev -> pytest / httpx for the test suite
pip install -e ".[vl,dev]"

# 3. Install a PaddlePaddle build matching your hardware (not pulled in automatically):
#    GPU (CUDA 12.6): pip install paddlepaddle-gpu==3.2.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
#    CPU:             pip install paddlepaddle==3.2.1     -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# 4. Configure secrets
cp .env.example .env   # set DOC2RAG_OPENAI_API_KEY for the medical advisor
```

- The first parse downloads the PaddleOCR-VL 1.6 weights (~1 GB) to `~/.paddlex/`.
- `.env` keys are documented in [`.env.example`](../.env.example). The `DOC2RAG_GCP_*` /
  `GOOGLE_APPLICATION_CREDENTIALS` entries are only needed for the legacy Document AI pipeline.
- Verify LLM keys without running a full parse: `python scripts/check_api_keys.py`.
- Run the tests: `pytest tests/test_vl_core.py` (no model weights needed) or `pytest` for the full suite.
