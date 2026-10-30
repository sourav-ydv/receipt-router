from receipts.drift import (
    alarm_index,
    decimal_share,
    detect_locale,
    evaluate_alarm,
    parse_total,
    read_box,
)
from receipts.drift import DriftWindow


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


def test_indonesian_samples_stay_idr():
    assert detect_locale(WARUNG) == "idr"
    assert detect_locale("TOTAL 5.000") == "idr"
    assert detect_locale("12,500") == "idr"
    assert detect_locale("100.00") == "idr"
    assert detect_locale("5,000.00") == "idr"
    assert detect_locale("47.619,00") == "idr"


def test_decimal_samples_are_decimal():
    ringgit = "TOTAL 9.00\nCASH 10.00\nCHANGE 1.00"
    assert detect_locale(ringgit) == "decimal"
    assert detect_locale("RM 1,234.50") == "decimal"
    assert detect_locale("1,234.50") == "decimal"
    assert detect_locale("MYR 16.50") == "decimal"


def test_a_thousands_group_wins_over_a_stray_small_decimal():
    assert detect_locale("Nasi 50.000\nService 9.00") == "idr"


def test_blank_text_stays_idr():
    assert detect_locale("") == "idr"
    assert detect_locale(None) == "idr"

def test_decimal_window_trips_when_it_fills():
    window = DriftWindow()
    text = "TOTAL 9.00\nCASH 10.00"
    for _ in range(19):
        assert window.observe(text, True) is False
    assert window.observe(text, True) is True
    assert window.alarmed is True
    assert window.observe("TOTAL 5.000", False) is True


def test_cord_rejection_rate_does_not_trip():
    window = DriftWindow()
    for i in range(20):
        assert window.observe("TOTAL 5.000", i < 4) is False
    assert window.alarmed is False