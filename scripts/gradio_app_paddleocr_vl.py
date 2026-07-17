"""Gradio demo for the PaddleOCR-VL parsing core (doc2rag baseline).

Thin UI over `doc2rag.vl` (parsing + interactive rendering) and
`doc2rag.advisor` (medical advice). Upload a PDF/image; hover a detected region
to highlight its parsed block (and vice-versa); read the recovered Markdown and
parsing JSON; optionally run the medical advisor + Tokyo hospital finder.

Run:
    python scripts/gradio_app_paddleocr_vl.py
The first parse downloads the PaddleOCR-VL weights (~1 GB).
"""

from __future__ import annotations

import html as html_lib
import json
import sys
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from doc2rag.advisor import build_advice_markdown  # noqa: E402
from doc2rag.vl import (  # noqa: E402
    INTERACTIVE_CSS,
    INTERACTIVE_HEAD,
    ParseOptions,
    build_interactive_html,
    get_parser,
)

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_IMAGE = ROOT / "data" / "健康診断.png"

# UI radio labels -> ParseOptions values.
_SHAPE = {"Auto": "auto", "Rectangle": "rect", "Quadrilateral": "quad", "Polygon": "poly"}
_PROMPT = {
    "Text": "ocr", "Formula": "formula", "Table": "table",
    "Chart": "chart", "Seal": "seal", "Text Spotting": "spotting",
}
# Auxiliary-content toggles: (UI label, ParseOptions field, hover explanation).
_AUX_UI = [
    ("Header", "parse_header", "Parse header regions instead of filtering them out."),
    ("Header Image", "parse_header_image", "Parse images located in the page header."),
    ("Footer", "parse_footer", "Parse footer regions instead of filtering them out."),
    ("Footer Image", "parse_footer_image", "Parse images located in the page footer."),
    ("Page Number", "parse_page_number", "Parse page-number text."),
    ("Footnote", "parse_footnote", "Parse footnote text."),
    ("Aside Text", "parse_aside_text", "Parse side / marginal text."),
]

WARNING = (
    "> ⚠️ **For reference only.** This automated analysis can be incomplete or "
    "incorrect and is **not** a medical diagnosis. Always double-check the "
    "results with a qualified doctor."
)


# --------------------------------------------------------------------- callbacks
def parse_document(
    file_path,
    # auxiliary-content toggles (order matches _AUX_UI)
    aux_header, aux_header_image, aux_footer, aux_footer_image,
    aux_number, aux_footnote, aux_aside_text,
    # model parameter settings
    orient, distort, layout, chart, seal, image_text,
    merge_tables, relevel_titles, shape_label, prompt_label_ui,
    repetition_penalty, temperature, top_p, min_pixels, max_pixels, nms,
):
    """Run the core parser and return (interactive_html, markdown, json, summary)."""
    if not file_path:
        return "", "", "", "Please upload a document first."

    opts = ParseOptions(
        parse_header=aux_header, parse_header_image=aux_header_image,
        parse_footer=aux_footer, parse_footer_image=aux_footer_image,
        parse_page_number=aux_number, parse_footnote=aux_footnote,
        parse_aside_text=aux_aside_text,
        orientation_correction=orient, distortion_correction=distort,
        layout_analysis=layout, chart_recognition=chart, seal_recognition=seal,
        image_text_recognition=image_text,
        merge_tables_across_pages=merge_tables, paragraph_title_recognition=relevel_titles,
        layout_shape=_SHAPE.get(shape_label, "auto"),
        prompt_type=_PROMPT.get(prompt_label_ui, "ocr"),
        repetition_penalty=float(repetition_penalty), temperature=float(temperature),
        top_p=float(top_p), min_pixels=int(min_pixels), max_pixels=int(max_pixels), nms=nms,
    )
    result = get_parser().parse(file_path, opts)

    html = build_interactive_html(result)
    # JSON tab: blocks + geometry, without the bulky embedded page images.
    json_str = json.dumps(
        [p.model_dump(exclude={"image"}) for p in result.pages],
        ensure_ascii=False, indent=2,
    )
    summary = (
        f"✅ PaddleOCR-VL {result.model_version} · pages={len(result.pages)} · "
        f"blocks={result.num_blocks} · layout={bool(layout)} · "
        f"shape={_SHAPE.get(shape_label, 'auto')}"
    )
    return html, result.markdown, json_str, summary


def analyze_health(markdown: str | None):
    """Medical advisor + Tokyo hospital recommendations over the parsed Markdown."""
    if not markdown or not markdown.strip():
        return "_Parse a document first, then click **Analyze & Recommend**._"
    try:
        return build_advice_markdown(markdown)
    except Exception as exc:  # noqa: BLE001 - surface errors in the UI
        return f"⚠️ Analysis failed: `{exc}`"


# --------------------------------------------------------------------- UI helpers
def _tip(label: str, tip: str):
    """A setting label with a hover-`?` tooltip (explanation in `data-tip`)."""
    return gr.HTML(
        f'<div class="pp-set"><span>{html_lib.escape(label)}</span>'
        f'<span class="pp-tip" tabindex="0" data-tip="{html_lib.escape(tip)}">?</span></div>'
    )


def _toggle(label: str, tip: str, value: bool):
    """Left: `?`-tooltip label; right: a compact checkbox. Returns the checkbox."""
    with gr.Row():
        with gr.Column(scale=5, min_width=120):
            _tip(label, tip)
        with gr.Column(scale=2, min_width=64):
            cb = gr.Checkbox(value=value, show_label=False, container=False)
    return cb


def _settings_panel() -> dict:
    """Build all parsing-setting controls (Auxiliary + Model) and return them
    keyed by name. Created wherever this is called (here: the Settings group)."""
    s: dict = {}

    with gr.Accordion("Auxiliary Content Parsing", open=False):
        gr.Markdown(
            "The model automatically identifies and filters auxiliary content; "
            "parsing will resume once the matching option is enabled.",
            elem_classes=["pp-aux-desc"],
        )
        aux = []
        for i in range(0, len(_AUX_UI), 2):
            with gr.Row():
                for lbl, _field, tip in _AUX_UI[i : i + 2]:
                    with gr.Column():
                        aux.append(_toggle(lbl, tip, False))
        s["aux_cbs"] = aux

    with gr.Accordion("Model Parameter Settings", open=False):
        with gr.Row():
            with gr.Column():
                s["orient"] = _toggle("Image Orientation Correction",
                    "Detect and correct rotated pages before parsing.", False)
            with gr.Column():
                s["distort"] = _toggle("Image Distortion Correction",
                    "Flatten curved / warped document photos before parsing.", False)
        with gr.Row():
            with gr.Column():
                s["layout"] = _toggle("Layout Analysis",
                    "Detect layout regions. Disable to run the VLM on the whole "
                    "image using the Prompt Type below.", True)
            with gr.Column():
                s["chart"] = _toggle("Chart Recognition",
                    "Recognize charts and convert them to structured data.", False)
        with gr.Row():
            with gr.Column():
                s["seal"] = _toggle("Seal Recognition",
                    "Recognize seals / stamps in the document.", True)
            with gr.Column():
                s["image_text"] = _toggle("Image Text Recognition",
                    "Run OCR on text found inside image blocks.", False)
        with gr.Row():
            with gr.Column():
                s["merge_tables"] = _toggle("Merge tables across pages",
                    "Merge tables split across consecutive pages (PDF only).", True)
            with gr.Column():
                s["relevel_titles"] = _toggle("Paragraph title level recognition",
                    "Rebuild the heading hierarchy across the document.", True)
        with gr.Row():
            with gr.Column():
                s["nms"] = _toggle("NMS Postprocessing",
                    "Apply non-maximum suppression to remove overlapping layout "
                    "boxes.", True)
            with gr.Column():
                gr.HTML("")

        _tip("Geometric Shape of Layout Detection Result",
             "Shape used to describe each detected region.")
        s["shape"] = gr.Radio(["Auto", "Rectangle", "Quadrilateral", "Polygon"],
                              value="Auto", show_label=False, container=False)
        _tip("Prompt Type Setting",
             "VLM recognition mode. Applies only when Layout Analysis is off.")
        s["prompt"] = gr.Radio(["Text", "Formula", "Table", "Chart", "Seal", "Text Spotting"],
                              value="Text", show_label=False, container=False)

        _tip("Repetition Suppression Strength",
             "Higher values discourage repeated text (repetition_penalty).")
        s["repetition_penalty"] = gr.Slider(1.0, 2.0, value=1.0, step=0.05,
                                       show_label=False, container=False)
        _tip("Recognition Stability",
             "Sampling temperature; 0 is the most deterministic / stable.")
        s["temperature"] = gr.Slider(0.0, 1.0, value=0.0, step=0.05,
                                show_label=False, container=False)
        _tip("Result Credible Range",
             "Nucleus-sampling range (top_p). 1.0 keeps the full distribution.")
        s["top_p"] = gr.Slider(0.0, 1.0, value=1.0, step=0.05,
                          show_label=False, container=False)
        with gr.Row():
            with gr.Column():
                _tip("Minimum Total Image Pixels",
                     "Lower bound for image size fed to the VLM (min_pixels).")
                s["min_pixels"] = gr.Number(value=147384, precision=0,
                                       show_label=False, container=False)
            with gr.Column():
                _tip("Maximum Total Image Pixels",
                     "Upper bound for image size fed to the VLM (max_pixels).")
                s["max_pixels"] = gr.Number(value=2822400, precision=0,
                                       show_label=False, container=False)
    return s


# --------------------------------------------------------------------------- UI
def build_demo() -> gr.Blocks:
    with gr.Blocks(title="doc2rag — PaddleOCR-VL") as demo:
        gr.Markdown(
            "# 📄 Interactive Health-Check Up\n"
            "Upload a document (PDF / image). Hover any detected region on the page "
            "and its parsed block lights up in the side panel (and the reverse).\n\n"
            "_First parse downloads the model weights (~1 GB)._"
        )

        with gr.Row():
            with gr.Column(scale=1):
                file_in = gr.File(
                    label="Document",
                    file_types=[".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"],
                    type="filepath",
                )
                with gr.Accordion("Settings", open=False):
                    s = _settings_panel()
                run_btn = gr.Button("🔍 Parse structure", variant="primary")
                if EXAMPLE_IMAGE.exists():
                    gr.Examples(examples=[[str(EXAMPLE_IMAGE)]], inputs=file_in, label="Example")
                status = gr.Markdown("")
            with gr.Column(scale=3):
                with gr.Tabs():
                    with gr.Tab("🔗 Interactive"):
                        html_out = gr.HTML()
                    with gr.Tab("📝 Markdown"):
                        md_out = gr.Markdown()
                    with gr.Tab("{ } JSON"):
                        json_out = gr.Code(language="json", label="Parsing result")

        # ---- medical advice + hospital finder (below the photo) ----
        gr.Markdown("---")
        gr.Markdown(WARNING)
        advice_btn = gr.Button("🩺 Analyze & Recommend", variant="secondary")
        advice_out = gr.Markdown()

        run_btn.click(
            fn=parse_document,
            inputs=[
                file_in, *s["aux_cbs"],
                s["orient"], s["distort"], s["layout"], s["chart"], s["seal"], s["image_text"],
                s["merge_tables"], s["relevel_titles"], s["shape"], s["prompt"],
                s["repetition_penalty"], s["temperature"], s["top_p"],
                s["min_pixels"], s["max_pixels"], s["nms"],
            ],
            outputs=[html_out, md_out, json_out, status],
        )

        # Signal the run immediately, do the slow work, then restore the button.
        advice_btn.click(
            fn=lambda: (
                gr.update(value="⏳ Analyzing…", interactive=False),
                "⏳ **Analyzing…** running the LLM medical advisor and Tokyo "
                "hospital lookup — this can take ~10–30 seconds.",
            ),
            outputs=[advice_btn, advice_out],
            queue=False,
        ).then(
            fn=analyze_health, inputs=md_out, outputs=advice_out,
        ).then(
            fn=lambda: gr.update(value="🩺 Analyze & Recommend", interactive=True),
            outputs=advice_btn, queue=False,
        )
    return demo


if __name__ == "__main__":
    build_demo().launch(theme=gr.themes.Soft(), css=INTERACTIVE_CSS, head=INTERACTIVE_HEAD)
