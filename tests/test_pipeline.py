import json

from receipts.drift import DriftWindow
from receipts.pipeline import RateBudget, Router
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
WRONG_TOTAL = GOOD.replace('"total": 5000', '"total": 9000')
SCALED = GOOD.replace("5000", "900")
IDR_TEXT = "Es Teh\n5.000\nTOTAL 5.000"


def student_says(raw):
    return lambda text: (raw, 0.5, 100)


class Teacher:
    def __init__(self, receipt, problems):
        self.receipt = receipt
        self.problems = problems
        self.calls = 0

    def __call__(self, text):
        self.calls += 1
        return "raw", self.receipt, self.problems, 800


def good_receipt():
    return Receipt(
        items=[LineItem(name="Es Teh", quantity=1, price=5000)],
        subtotal=5000,
        total=5000,
    )


def decimal_receipt():
    return Receipt(
        items=[LineItem(name="Pen", quantity=1, price=9)],
        subtotal=9,
        total=9,
    )


def test_clean_student_answer_never_reaches_the_teacher():
    teacher = Teacher(good_receipt(), [])
    result = Router(student_says(GOOD), teacher).extract(IDR_TEXT)
    assert result.source == "student"
    assert not result.needs_review
    assert teacher.calls == 0


def test_bad_student_answer_goes_to_the_teacher():
    teacher = Teacher(good_receipt(), [])
    result = Router(student_says(WRONG_TOTAL), teacher).extract("text")
    assert result.source == "teacher"
    assert result.teacher_called
    assert not result.needs_review
    assert teacher.calls == 1


def test_unparseable_student_answer_is_escalated():
    teacher = Teacher(good_receipt(), [])
    result = Router(student_says("no idea"), teacher).extract("text")
    assert result.source == "teacher"


def test_teacher_that_also_fails_is_flagged_for_review():
    teacher = Teacher(good_receipt(), ["items_vs_subtotal"])
    result = Router(student_says(WRONG_TOTAL), teacher).extract("text")
    assert result.needs_review
    assert result.problems == ["items_vs_subtotal"]


def test_without_a_teacher_the_student_answer_is_flagged():
    result = Router(student_says(WRONG_TOTAL)).extract("text")
    assert result.source == "student"
    assert result.needs_review
    assert result.teacher_called is False


def test_exhausted_budget_keeps_the_teacher_out():
    teacher = Teacher(good_receipt(), [])
    router = Router(student_says(WRONG_TOTAL), teacher, RateBudget(1))
    router.extract("one")
    second = router.extract("two")
    assert teacher.calls == 1
    assert second.needs_review


def test_teacher_errors_do_not_crash_the_request():
    def broken(text):
        raise RuntimeError("network")

    result = Router(student_says(WRONG_TOTAL), broken).extract("text")
    assert result.needs_review


def test_escalations_are_logged_when_a_path_is_given(tmp_path):
    path = tmp_path / "log.jsonl"
    teacher = Teacher(good_receipt(), [])
    Router(student_says(WRONG_TOTAL), teacher, log_path=str(path)).extract("some text")
    record = json.loads(path.read_text().splitlines()[0])
    assert record["text"] == "some text"
    assert record["teacher_called"] is True
    assert record["locale"] == "idr"
    assert record["drift_alarm"] is False


def test_log_lines_record_both_locales(tmp_path):
    path = tmp_path / "log.jsonl"
    teacher = Teacher(good_receipt(), [])
    router = Router(student_says(WRONG_TOTAL), teacher, log_path=str(path))
    router.extract("TOTAL 5.000")
    router.extract("TOTAL 9.00")
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [line["locale"] for line in lines] == ["idr", "decimal"]
    assert lines[0]["drift_alarm"] is False
    assert lines[1]["drift_alarm"] is False


def test_budget_window_expires():
    now = [0.0]
    budget = RateBudget(2, window=10.0, clock=lambda: now[0])
    assert budget.take() and budget.take()
    assert not budget.take()
    now[0] = 11.0
    assert budget.take()


def test_decimal_receipt_goes_to_the_teacher():
    teacher = Teacher(decimal_receipt(), [])
    result = Router(student_says(SCALED), teacher).extract("TOTAL 9.00")
    assert result.source == "teacher"
    assert result.receipt.total == 9
    assert result.teacher_called
    assert not result.needs_review
    assert teacher.calls == 1

DECIMAL_GOOD = json.dumps(
    {
        "items": [{"name": "Pen", "quantity": 1, "price": 9, "discount": 0}],
        "subtotal": 9,
        "discount": None,
        "service": None,
        "tax": None,
        "total": 9,
    }
)


def test_a_grounded_decimal_receipt_stays_with_the_student():
    teacher = Teacher(decimal_receipt(), [])
    result = Router(student_says(DECIMAL_GOOD), teacher).extract("Pen\n9.00\nTOTAL 9.00")
    assert result.source == "student"
    assert result.receipt.total == 9
    assert not result.needs_review
    assert teacher.calls == 0


def test_a_decimal_cash_amount_still_goes_to_the_teacher():
    parking = json.dumps(
        {
            "items": [{"name": "PAY PARKING TICKET", "quantity": 1, "price": 1.5, "discount": 0}],
            "subtotal": None,
            "discount": None,
            "service": None,
            "tax": 0,
            "total": 2,
        }
    )
    teacher = Teacher(decimal_receipt(), [])
    result = Router(student_says(parking), teacher).extract("PAY PARKING TICKET\n1.50\nTOTAL 2.00")
    assert result.source == "teacher"
    assert teacher.calls == 1


def test_failed_decimal_teacher_needs_review():
    scaled = decimal_receipt()
    scaled.total = 900
    teacher = Teacher(scaled, ["ungrounded_amount"])
    result = Router(student_says(SCALED), teacher).extract("TOTAL 9.00")
    assert result.source == "teacher"
    assert result.needs_review
    assert result.problems == ["ungrounded_amount"]


def test_drift_alarm_leaves_a_passing_receipt_with_the_student():
    window = DriftWindow()
    teacher = Teacher(good_receipt(), [])
    router = Router(student_says(GOOD), teacher, drift=window)
    for _ in range(20):
        router.extract("TOTAL 9.00\nCASH 10.00")
    assert window.alarmed is True
    assert teacher.calls == 20
    follow = router.extract(IDR_TEXT)
    assert follow.source == "student"
    assert follow.teacher_called is False
    assert teacher.calls == 20


def test_idr_stream_does_not_trip_the_drift_alarm():
    window = DriftWindow()
    teacher = Teacher(good_receipt(), [])
    router = Router(student_says(GOOD), teacher, drift=window)
    for i in range(20):
        text = "bad" if i < 4 else IDR_TEXT
        result = router.extract(text)
        if i >= 4:
            assert result.source == "student"
    assert window.alarmed is False
    assert teacher.calls == 4