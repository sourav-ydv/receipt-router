import pytest

from receipts.money import money_tokens
from receipts.parsing import to_number

WARUNG = """WARUNG BU SARI
2
Nasi Ayam
50.000
1
Es Teh
5.000
ITEMS 2
SUBTTL 55.000
PB-1 10% 5.500
TOTAL 60.500
CASH 100.000"""


def test_idr_receipt_uses_thousands_separators():
    assert money_tokens(WARUNG, "idr") == [
        2.0,
        50000.0,
        1.0,
        5000.0,
        2.0,
        55000.0,
        10.0,
        5500.0,
        60500.0,
        100000.0,
    ]
    assert money_tokens("TOTAL 5.000", "idr") == [5000.0]
    assert money_tokens("100.00", "idr") == [100.0]
    assert money_tokens("5,000.00", "idr") == [5000.0]
    assert money_tokens("47.619,00", "idr") == [47619.0]


def test_decimal_receipt_keeps_cents():
    ringgit = "TOTAL 9.00\nCASH 10.00\nCHANGE 1.00"
    assert money_tokens(ringgit, "decimal") == [9.0, 10.0, 1.0]
    assert money_tokens("RM 1,234.50", "decimal") == [1234.5]
    assert money_tokens("RM1,234.50", "decimal") == [1234.5]
    assert money_tokens("1,234.50", "decimal") == [1234.5]
    assert money_tokens("MYR 16.50", "decimal") == [16.5]
    assert money_tokens("1.234,50", "decimal") == [1234.5]


def test_nine_depends_on_the_locale():
    assert money_tokens("9.00", "decimal") == [9.0]
    assert money_tokens("9.00", "idr") == [900.0]


def test_old_parser_still_reads_nine_as_nine_hundred():
    assert to_number("9.00") == 900.0


def test_discounts_are_stored_as_positive_amounts():
    assert money_tokens("DISC -7,800", "idr") == [7800.0]
    assert money_tokens("DISC -2.50", "decimal") == [2.5]


def test_blank_text_has_no_tokens():
    assert money_tokens("", "idr") == []
    assert money_tokens(None, "decimal") == []


def test_unknown_locale_is_rejected():
    with pytest.raises(ValueError):
        money_tokens("9.00", "usd")