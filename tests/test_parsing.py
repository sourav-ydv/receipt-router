from receipts.parsing import receipt_from_cord, text_from_cord, to_number


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
