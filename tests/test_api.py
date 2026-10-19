import json

from fastapi.testclient import TestClient

from receipts.api import create_app
from receipts.pipeline import Router

GOOD = json.dumps(
    {
        "items": [{"name": "Es Teh", "quantity": 1, "price": 5000, "discount": 0}],
        "subtotal": 5000,
        "discount": None,
        "service": None,
        "tax": None,
        "total": 5000,
    }
)


def client():
    router = Router(lambda text: (GOOD, 0.1, 50))
    return TestClient(create_app(lambda: router))


def test_health():
    with client() as c:
        assert c.get("/health").json() == {"status": "ok"}


def test_extract_returns_the_receipt():
    with client() as c:
        body = c.post("/extract", json={"text": "TOTAL 5.000"}).json()
    assert body["source"] == "student"
    assert body["receipt"]["total"] == 5000


def test_empty_text_is_rejected():
    with client() as c:
        assert c.post("/extract", json={"text": ""}).status_code == 422


def test_home_page_has_a_textarea():
    with client() as c:
        assert "<textarea" in c.get("/").text
