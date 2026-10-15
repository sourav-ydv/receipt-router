from receipts.parsing import (
    is_usable,
    parse_quantity,
    receipt_from_cord,
    text_from_cord,
    to_number,
)


def test_to_number_strips_separators():
    assert to_number("16,500") == 16500.0
    assert to_number("1.346.000") == 1346000.0
    assert to_number("Rp 2.000") == 2000.0


def test_to_number_handles_missing():
    assert to_number(None) is None
    assert to_number("n/a") is None


def test_single_menu_item_given_as_dict():
    parsed = {"menu": {"nm": "Latte", "cnt": "2", "price": "40,000"}}
    receipt = receipt_from_cord(parsed)
    assert len(receipt.items) == 1
    assert receipt.items[0].quantity == 2
    assert receipt.items[0].price == 40000.0


def test_full_receipt():
    parsed = {
        "menu": [
            {"nm": "Nasi Goreng", "cnt": "1", "price": "25,000"},
            {"nm": "Es Teh", "cnt": "2", "price": "10,000"},
        ],
        "sub_total": {"subtotal_price": "35,000", "tax_price": "3,500"},
        "total": {"total_price": "38,500"},
    }
    receipt = receipt_from_cord(parsed)
    assert receipt.subtotal == 35000.0
    assert receipt.tax == 3500.0
    assert receipt.total == 38500.0
    assert [i.name for i in receipt.items] == ["Nasi Goreng", "Es Teh"]


def test_missing_sections_do_not_crash():
    receipt = receipt_from_cord({})
    assert receipt.items == []
    assert receipt.total is None


def test_text_from_cord_joins_words_per_line():
    valid = [
        {"words": [{"text": "NASI"}, {"text": "GORENG"}]},
        {"words": []},
        {"words": [{"text": "25,000"}]},
    ]
    assert text_from_cord(valid) == "NASI GORENG\n25,000"


def test_to_number_keeps_negative_sign():
    assert to_number("-7,800") == -7800.0
    assert to_number("-45") == -45.0


def test_item_discount_is_stored_as_positive_amount():
    parsed = {"menu": {"nm": "Wajik", "price": "7,000", "discountprice": "-2,100"}}
    item = receipt_from_cord(parsed).items[0]
    assert item.price == 7000.0
    assert item.discount == 2100.0


def test_service_and_receipt_discount_are_read():
    parsed = {
        "menu": {"nm": "Chicken", "cnt": "1", "price": "190,000"},
        "sub_total": {
            "subtotal_price": "190,000",
            "discount_price": "19,000",
            "service_price": "9,600",
            "tax_price": "52,416",
        },
        "total": {"total_price": "233,016"},
    }
    receipt = receipt_from_cord(parsed)
    assert receipt.discount == 19000.0
    assert receipt.service == 9600.0


def test_list_valued_amounts_use_the_first_entry():
    parsed = {
        "menu": {"nm": "KFC Winger HC", "cnt": "1", "price": "20,000"},
        "sub_total": {"subtotal_price": ["20,000", "20,000"], "tax_price": "2,000"},
        "total": {"total_price": ["55,834", "55,800"]},
    }
    receipt = receipt_from_cord(parsed)
    assert receipt.subtotal == 20000.0
    assert receipt.total == 55834.0


def test_list_valued_item_discounts_are_summed():
    parsed = {
        "menu": {
            "nm": "BENECOL LYCHEE 2S",
            "price": "14,000",
            "discountprice": ["1,400 -", "1,260-"],
        }
    }
    assert receipt_from_cord(parsed).items[0].discount == 2660.0


def test_quantity_formats():
    assert parse_quantity("1 x") == 1
    assert parse_quantity("3") == 3
    assert parse_quantity("2X") == 2
    assert parse_quantity("0.264X") == 1
    assert parse_quantity("0,292X") == 1
    assert parse_quantity(["TRIPPLE CHEESE", "1"]) == 1
    assert parse_quantity(None) == 1


def test_receipts_with_nameless_items_are_not_usable():
    nameless = {
        "menu": [{"unitprice": "12.000", "cnt": "3", "price": "36.000"}],
        "total": {"total_price": "36.000"},
    }
    no_total = {
        "menu": {"nm": "Cuka", "price": "289000"},
        "total": {"cashprice": "300000"},
    }
    fine = {
        "menu": {"nm": "Cuka", "price": "289000"},
        "total": {"total_price": "289000"},
    }
    assert is_usable(nameless) is False
    assert is_usable(no_total) is False
    assert is_usable(fine) is True
