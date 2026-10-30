import json

from fastapi.testclient import TestClient

from receipts.api import create_app
from receipts.pipeline import Router
from receipts.schema import LineItem, Receipt

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
SCALED = GOOD.replace("5000", "900")


def client():
    router = Router(lambda text: (GOOD, 0.1, 50))
    return TestClient(create_app(lambda: router))


def decimal_receipt():
    return Receipt(
        items=[LineItem(name="Pen", quantity=1, price=9)],
        subtotal=9,
        total=9,
    )


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


def test_grounded_idr_receipt_stays_with_the_student():
    calls = {"n": 0}

    def teacher(text):
        calls["n"] += 1
        return "raw", decimal_receipt(), [], 10

    router = Router(lambda text: (GOOD, 0.1, 50), teacher)
    with TestClient(create_app(lambda: router)) as c:
        body = c.post("/extract", json={"text": "TOTAL 5.000"}).json()
    assert body["source"] == "student"
    assert body["receipt"]["total"] == 5000
    assert calls["n"] == 0


def test_decimal_receipt_uses_the_teacher():
    calls = {"n": 0}

    def teacher(text):
        calls["n"] += 1
        return "raw", decimal_receipt(), [], 10

    router = Router(lambda text: (SCALED, 0.1, 50), teacher)
    with TestClient(create_app(lambda: router)) as c:
        body = c.post("/extract", json={"text": "TOTAL 9.00"}).json()
    assert body["source"] == "teacher"
    assert body["receipt"]["total"] == 9
    assert body["needs_review"] is False
    assert calls["n"] == 1

def test_a_grounded_decimal_receipt_stays_with_the_student():
    calls = {"n": 0}
    answer = json.dumps(
        {
            "items": [{"name": "Pen", "quantity": 1, "price": 9, "discount": 0}],
            "subtotal": 9,
            "discount": None,
            "service": None,
            "tax": None,
            "total": 9,
        }
    )

    def teacher(text):
        calls["n"] += 1
        return "raw", decimal_receipt(), [], 10

    router = Router(lambda text: (answer, 0.1, 50), teacher)
    with TestClient(create_app(lambda: router)) as c:
        body = c.post("/extract", json={"text": "Pen\n9.00\nTOTAL 9.00"}).json()
    assert body["source"] == "student"
    assert body["receipt"]["total"] == 9
    assert calls["n"] == 0