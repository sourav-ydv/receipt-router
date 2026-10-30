import json

from receipts.formatting import compact, make_example
from receipts.schema import LineItem, Receipt
from receipts.validators import parse_receipt


def sample():
    return Receipt(
        items=[LineItem(name="Nasi Ayam", quantity=2, price=50000.0)],
        subtotal=50000.0,
        tax=5000.0,
        total=55000.0,
    )


def test_whole_numbers_are_written_without_decimals():
    data = json.loads(compact(sample()))
    assert data["total"] == 55000
    assert "55000.0" not in compact(sample())
    assert data["discount"] is None


def test_compact_output_round_trips_through_the_parser():
    assert parse_receipt(compact(sample())) == sample()


def test_example_has_system_user_assistant_turns():
    example = make_example("TOTAL 55.000", sample())
    roles = [m["role"] for m in example["messages"]]
    assert roles == ["system", "user", "assistant"]
    assert example["messages"][1]["content"] == "TOTAL 55.000"

def test_default_instruction_stays_the_one_liner():
    example = make_example("TOTAL 55.000", sample())
    assert example["messages"][0]["content"] == "Extract the receipt fields as JSON."


def test_locale_instructions_differ():
    idr = make_example("TOTAL 55.000", sample(), locale="idr")
    decimal = make_example("TOTAL 9.00", sample(), locale="decimal")
    assert "12.500 means 12500" in idr["messages"][0]["content"]
    assert "9.00 means 9" in decimal["messages"][0]["content"]
    assert idr["messages"][0]["content"] != decimal["messages"][0]["content"]