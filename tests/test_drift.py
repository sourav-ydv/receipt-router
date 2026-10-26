from receipts.drift import (
    alarm_index,
    decimal_share,
    evaluate_alarm,
    parse_total,
    read_box,
)


def test_totals_with_currency_marks_are_read():
    assert parse_total("9.00") == 9.0
    assert parse_total("RM 9.00") == 9.0
    assert parse_total("$9.99") == 9.99
    assert parse_total("RM1,234.50") == 1234.5


def test_missing_or_broken_totals_give_none():
    assert parse_total("") is None
    assert parse_total(None) is None
    assert parse_total("n/a") is None


def test_box_file_keeps_text_with_commas(tmp_path):
    path = tmp_path / "000.csv"
    path.write_text(
        "72,25,326,25,326,64,72,64,TAN WOON YANN\n"
        "110,144,383,144,383,163,110,163,NO.53 55,57 & 59, JALAN SAGU 18,\n"
        "1,2,3,4,5,6,7,8,\n"
    )
    assert read_box(path) == "TAN WOON YANN\nNO.53 55,57 & 59, JALAN SAGU 18,"


def test_two_digit_decimals_mark_malaysian_style_receipts():
    rupiah = "Nasi Ayam\n25.000\nTOTAL 60.500\n1,346,000"
    ringgit = "TOTAL 9.00\nCASH 10.00\nCHANGE 1.00"
    assert decimal_share(rupiah) == 0.0
    assert decimal_share(ringgit) == 1.0


def test_stable_stream_raises_no_alarm():
    baseline = [0.0, 1.0] * 20
    assert alarm_index([0.0, 1.0] * 30, baseline) is None


def test_shift_is_caught_once_the_window_fills():
    baseline = [0.0] * 40
    index = alarm_index([1.0] * 40, baseline, window=20)
    assert index is not None
    assert index < 20


def test_evaluation_reports_false_alarms_and_delay():
    baseline = [0.0, 0.1] * 20
    result = evaluate_alarm(baseline, [0.0, 0.1] * 20, [1.0] * 40)
    assert result["false_alarm"] is False
    assert 1 <= result["delay"] <= 20
    noisy = evaluate_alarm(baseline, [1.0] * 40, [1.0] * 40)
    assert noisy["false_alarm"] is True
