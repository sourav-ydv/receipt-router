from receipts.parsing import receipt_from_cord
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


def test_service_charge_and_discount_are_part_of_the_total():
    parsed = {
        "menu": [
            {"nm": "Bintang Bremer", "cnt": "1", "price": "59,000"},
            {"nm": "Chicken H-H", "cnt": "1", "price": "190,000"},
            {"nm": "Ades", "cnt": "1", "price": "10,000"},
        ],
        "sub_total": {
            "subtotal_price": "259,000",
            "discount_price": "19,000",
            "service_price": "9,600",
            "tax_price": "52,416",
        },
        "total": {"total_price": "302,016"},
    }
    assert check(receipt_from_cord(parsed)) == []


def test_item_level_discounts_reduce_the_items_sum():
    parsed = {
        "menu": [
            {"nm": "BUBUR UNGU", "discountprice": "-7,800", "price": "26,000"},
            {"nm": "SENDOK BEBEK", "price": "0"},
            {"nm": "WAJIK", "discountprice": "-2,100", "price": "7,000"},
            {"nm": "CENTIK MANIS", "discountprice": "-1,650", "price": "5,500"},
            {"nm": "PLASTIK SEDANG", "price": "0"},
        ],
        "sub_total": {"subtotal_price": "26,950"},
        "total": {"total_price": "26,950", "cashprice": "26,950"},
    }
    assert check(receipt_from_cord(parsed)) == []


def test_tax_inclusive_receipt_passes():
    parsed = {
        "menu": {"nm": "MINI CHOCO", "price": "13,500"},
        "sub_total": {"subtotal_price": "12,273", "tax_price": "1,227"},
        "total": {"total_price": "13,500", "cashprice": "14,000"},
    }
    assert check(receipt_from_cord(parsed)) == []


def test_small_rounding_gap_on_a_large_total_is_tolerated():
    receipt = make([("a", 1, 1346000)], subtotal=1346000, tax=144695, total=1591600)
    receipt.service = 100950
    assert check(receipt) == []


def test_duplicate_subtotal_entries_do_not_break_the_check():
    parsed = {
        "menu": [
            {"nm": "BASO TAHU", "unitprice": "43.636", "cnt": "1", "price": "43.636"},
            {"nm": "NASI PUTIH", "unitprice": "6.000", "cnt": "1", "price": "6.000"},
        ],
        "sub_total": {"subtotal_price": ["49.636", "49.636"], "tax_price": "4.964"},
        "total": {"total_price": "54.600", "cashprice": "60.100"},
    }
    assert check(receipt_from_cord(parsed)) == []


def test_weighted_items_with_fractional_counts():
    parsed = {
        "menu": [
            {"nm": "IKAN GABUS FRESH", "unitprice": "98,500", "cnt": "0.264X", "price": "26,004"},
            {"nm": "IKAN BUMBU KUNING", "unitprice": "72,500", "cnt": "0.308X", "price": "22,330"},
            {"nm": "OCTOPUS SATAY", "unitprice": "7,500", "cnt": "1X", "price": "7,500"},
        ],
        "sub_total": {"subtotal_price": "55,834"},
        "total": {"total_price": ["55,834", "55,800"], "cashprice": "60,000"},
    }
    assert check(receipt_from_cord(parsed)) == []


def test_several_discounts_on_one_item():
    parsed = {
        "menu": [
            {"nm": "A", "cnt": "1X", "discountprice": "800-", "price": "8,000"},
            {"nm": "B", "cnt": "1X", "discountprice": ["1,400 -", "1,260-"], "price": "14,000"},
            {"nm": "C", "cnt": "1X", "discountprice": "1,220-", "price": "12,200"},
            {"nm": "D", "cnt": "1X", "discountprice": "600-", "price": "6,000"},
            {"nm": "E", "cnt": "1X", "discountprice": "640-", "price": "6,400"},
            {"nm": "F", "cnt": "1X", "discountprice": ["1,400 -", "790-"], "price": "9,300"},
            {"nm": "G", "cnt": "0,292X", "discountprice": "581-", "price": "5,811"},
        ],
        "sub_total": {"subtotal_price": "53,020"},
        "total": {"total_price": "53,020"},
    }
    assert check(receipt_from_cord(parsed)) == []
