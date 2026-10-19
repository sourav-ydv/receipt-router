import gradio as gr

from receipts.api import SAMPLE
from receipts.config import MAX_INPUT_CHARS

INTRO = (
    "Paste the OCR text of a receipt. A small model reads it first. "
    "If its answer fails the arithmetic checks, the receipt goes to a larger model."
)


def describe(result):
    if result.source == "student" and not result.needs_review:
        return f"Answered by the small model in {result.student_seconds:.1f} s."
    if result.source == "teacher" and not result.needs_review:
        return "The small model's answer failed a check, so the larger model answered."
    return "No answer passed every check. Please review this one by hand."


def make_app(router):
    def run(text):
        text = text.strip()
        if not text:
            return "Paste some receipt text first.", {}
        result = router.extract(text[:MAX_INPUT_CHARS])
        return describe(result), result.model_dump()

    with gr.Blocks(title="receipt-router") as demo:
        gr.Markdown("# receipt-router")
        gr.Markdown(INTRO)
        box = gr.Textbox(value=SAMPLE, lines=14, label="Receipt text")
        button = gr.Button("Extract")
        status = gr.Textbox(label="Status", interactive=False)
        output = gr.JSON(label="Result")
        button.click(run, box, [status, output])
    return demo


if __name__ == "__main__":
    from receipts.server import build_router

    app = make_app(build_router())
    app.queue(max_size=8)
    app.launch(server_name="0.0.0.0", server_port=7860)
