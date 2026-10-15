from receipts.schema import LineItem, Receipt
from receipts.scoring import score, summarize


def receipt(items, total):
    return Receipt(
        items=[LineItem(name=n, quantity=1, price=p) for n, p in items],
        total=total,
    )


def test_identical_receipts_score_perfectly():
    r = receipt([("a", 10), ("b", 20)], 30)
    result = score(r, r)
    assert result["exact"] is True
    assert result["items_f1"] == 1.0


def test_item_names_ignore_case_and_padding():
    pred = receipt([(" Latte ", 10)], 10)
    gold = receipt([("latte", 10)], 10)
    assert score(pred, gold)["items_f1"] == 1.0


def test_partial_item_match():
    pred = receipt([("a", 10), ("c", 99)], 10)
    gold = receipt([("a", 10), ("b", 20)], 30)
    result = score(pred, gold)
    assert result["items_f1"] == 0.5
    assert result["total"] is False


def test_both_empty_counts_as_match():
    assert score(Receipt(), Receipt())["items_f1"] == 1.0


def test_summarize_averages_each_field():
    a = receipt([("a", 10)], 10)
    b = receipt([("x", 5)], 7)
    summary = summarize([score(a, a), score(b, a)])
    assert summary["total"] == 0.5
    assert summary["exact"] == 0.5
