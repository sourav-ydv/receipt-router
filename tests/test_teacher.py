from types import SimpleNamespace

from receipts.teacher import build_messages, label


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


def test_messages_end_with_the_receipt_text():
    messages = build_messages("TOTAL 5.000")
    assert messages[0]["role"] == "system"
    assert messages[-1] == {"role": "user", "content": "TOTAL 5.000"}


def test_clean_answer_has_no_problems():
    raw, receipt, problems, tokens = label(FakeClient(GOOD), "text")
    assert receipt.total == 5000.0
    assert problems == []


def test_fenced_answer_is_still_parsed():
    raw, receipt, problems, tokens = label(FakeClient("```json\n" + GOOD + "\n```"), "text")
    assert receipt is not None
    assert problems == []


def test_wrong_arithmetic_is_flagged():
    bad = GOOD.replace('"total": 5000', '"total": 9000')
    raw, receipt, problems, tokens = label(FakeClient(bad), "text")
    assert problems == ["subtotal_tax_total"]


def test_garbage_is_unparseable():
    raw, receipt, problems, tokens = label(FakeClient("I cannot read this"), "text")
    assert receipt is None
    assert problems == ["unparseable"]
