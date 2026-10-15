from receipts.schema import LineItem, Receipt
from receipts.validators import check, parse_receipt


def make(items, subtotal=None, tax=None, total=None):
    return Receipt(
        items=[LineItem(name=n, quantity=q, price=p) for n, q, p in items],
        subtotal=subtotal,
        tax=tax,
        total=total,
    )


def test_clean_receipt_passes():
    receipt = make([("a", 1, 100), ("b", 1, 50)], subtotal=150, tax=15, total=165)
    assert check(receipt) == []


def test_items_that_do_not_add_up_are_flagged():
    receipt = make([("a", 1, 100), ("b", 1, 50)], subtotal=200, tax=0, total=200)
    assert "items_vs_subtotal" in check(receipt)


def test_total_without_subtotal_checks_against_items():
    good = make([("a", 1, 100), ("b", 1, 50)], total=150)
    bad = make([("a", 1, 100), ("b", 1, 50)], total=999)
    assert check(good) == []
    assert "items_vs_subtotal" in check(bad)


def test_tax_arithmetic_is_flagged():
    receipt = make([("a", 1, 100)], subtotal=100, tax=10, total=500)
    assert "subtotal_tax_total" in check(receipt)


def test_empty_receipt_reports_both_problems():
    problems = check(Receipt())
    assert "no_items" in problems
    assert "missing_total" in problems


def test_parse_receipt_accepts_fenced_json():
    raw = '```json\n{"items": [{"name": "x", "price": 5}], "total": 5}\n```'
    receipt = parse_receipt(raw)
    assert receipt is not None
    assert receipt.total == 5.0


def test_parse_receipt_rejects_bad_output():
    assert parse_receipt("sorry, I cannot read this") is None
    assert parse_receipt('{"items": "none"}') is None
