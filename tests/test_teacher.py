from types import SimpleNamespace

from receipts.teacher import build_messages, label
from receipts.teacher import cord_tasks, file_tasks, remaining

class FakeClient:
    def __init__(self, content):
        message = SimpleNamespace(content=content)
        choice = SimpleNamespace(message=message)
        usage = SimpleNamespace(total_tokens=100)
        response = SimpleNamespace(choices=[choice], usage=usage)
        create = lambda **kwargs: response
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


GOOD = (
    '{"items": [{"name": "Es Teh", "quantity": 1, "price": 5000, "discount": 0}],'
    ' "subtotal": 5000, "discount": null, "service": null, "tax": null, "total": 5000}'
)
IDR_TEXT = "Es Teh\n5.000\nSUBTOTAL 5.000\nTOTAL 5.000"
DECIMAL_GOOD = (
    '{"items": [{"name": "Pen", "quantity": 1, "price": 9, "discount": 0}],'
    ' "subtotal": 9, "discount": null, "service": null, "tax": null, "total": 9}'
)
SCALED = (
    '{"items": [{"name": "Pen", "quantity": 1, "price": 900, "discount": 0}],'
    ' "subtotal": 900, "discount": null, "service": null, "tax": null, "total": 900}'
)


def test_messages_end_with_the_receipt_text():
    messages = build_messages("TOTAL 5.000")
    assert messages[0]["role"] == "system"
    assert messages[-1] == {"role": "user", "content": "TOTAL 5.000"}


def test_indonesian_prompt_keeps_the_thousands_rule():
    messages = build_messages("TOTAL 5.000")
    assert "12.500 and 12,500 both mean 12500." in messages[0]["content"]
    assert "50.000" in messages[1]["content"]


def test_decimal_prompt_uses_cents():
    messages = build_messages("TOTAL 9.00")
    assert "9.00 means 9" in messages[0]["content"]
    assert "12500" not in messages[0]["content"]
    assert "50.000" not in messages[1]["content"]
    assert '"price": 9' in messages[2]["content"]


def test_explicit_locale_picks_the_prompt():
    messages = build_messages("TOTAL 9.00", locale="idr")
    assert "12500" in messages[0]["content"]
    assert "50.000" in messages[1]["content"]


def test_clean_answer_has_no_problems():
    raw, receipt, problems, tokens = label(FakeClient(GOOD), IDR_TEXT)
    assert receipt.total == 5000.0
    assert problems == []


def test_fenced_answer_is_still_parsed():
    raw, receipt, problems, tokens = label(FakeClient("```json\n" + GOOD + "\n```"), IDR_TEXT)
    assert receipt is not None
    assert problems == []


def test_wrong_arithmetic_is_flagged():
    bad = GOOD.replace('"total": 5000', '"total": 9000')
    text = "Es Teh\n5.000\nSUBTOTAL 5.000\nTOTAL 9.000"
    raw, receipt, problems, tokens = label(FakeClient(bad), text)
    assert problems == ["subtotal_tax_total"]


def test_garbage_is_unparseable():
    raw, receipt, problems, tokens = label(FakeClient("I cannot read this"), "text")
    assert receipt is None
    assert problems == ["unparseable"]


def test_decimal_answer_that_keeps_cents_passes():
    raw, receipt, problems, tokens = label(FakeClient(DECIMAL_GOOD), "TOTAL 9.00")
    assert receipt.total == 9
    assert problems == []


def test_scaled_decimal_answer_is_flagged():
    raw, receipt, problems, tokens = label(FakeClient(SCALED), "TOTAL 9.00")
    assert receipt.total == 900
    assert problems == ["ungrounded_amount"]

def test_cord_tasks_keep_usable_row_indexes():
    rows = [
        {"usable": True, "text": "TOTAL 5.000"},
        {"usable": False, "text": "skip"},
        {"usable": True, "text": "TOTAL 9.00"},
    ]
    assert cord_tasks(rows) == [
        {"id": 0, "text": "TOTAL 5.000"},
        {"id": 2, "text": "TOTAL 9.00"},
    ]

def test_file_tasks_keep_the_given_ids():
    rows = [
        {"id": "376", "text": "TOTAL 9.00", "total": 9.0},
        {"id": "12", "text": "", "total": 1.0},
    ]
    assert file_tasks(rows) == [{"id": "376", "text": "TOTAL 9.00"}]
    
def test_remaining_skips_finished_ids_and_applies_the_limit():
    rows = [
        {"id": "a", "text": "1"},
        {"id": "b", "text": "2"},
        {"id": "c", "text": "3"},
    ]
    assert remaining(rows, {"b"}) == [rows[0], rows[2]]
    assert remaining(rows, set(), limit=2) == rows[:2]
    assert remaining(rows, set(), limit=None) == rows