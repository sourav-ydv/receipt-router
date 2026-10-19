from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .config import MAX_INPUT_CHARS

SAMPLE = """WARUNG BU SARI
2
Nasi Ayam
50.000
1
Es Teh
5.000
SUBTTL 55.000
PB-1 10% 5.500
TOTAL 60.500"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>receipt-router</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; }
textarea { width: 100%; height: 14rem; font-family: monospace; }
pre { background: #f4f4f4; padding: 1rem; overflow-x: auto; }
button { padding: 0.5rem 1.2rem; margin-top: 0.5rem; }
</style>
</head>
<body>
<h1>receipt-router</h1>
<p>Paste the OCR text of a receipt. A small model reads it first. If its answer fails the arithmetic checks, the receipt goes to a larger model.</p>
<textarea id="text">__SAMPLE__</textarea>
<br>
<button id="go">Extract</button>
<pre id="out"></pre>
<script>
document.getElementById("go").onclick = async () => {
  const out = document.getElementById("out");
  out.textContent = "working...";
  const res = await fetch("/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: document.getElementById("text").value }),
  });
  out.textContent = JSON.stringify(await res.json(), null, 2);
};
</script>
</body>
</html>
""".replace("__SAMPLE__", SAMPLE)


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)


def create_app(make_router):
    @asynccontextmanager
    async def lifespan(app):
        app.state.router = make_router()
        yield

    app = FastAPI(title="receipt-router", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/extract")
    def extract(request: ExtractRequest):
        return app.state.router.extract(request.text)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return PAGE

    return app
