import re
import threading
from collections import deque

DECIMAL_AMOUNT = re.compile(r"\d[.,]\d{2}(?!\d)")
IDR_GROUP = re.compile(r"\d{1,3}(?:\.\d{3})+")
SMALL_DECIMAL = re.compile(r"(?<!\d)\d{1,2}[.,]\d{2}(?!\d)")
COMMA_CENTS = re.compile(r"\d{1,3}(?:,\d{3})+\.(?!00(?:\D|$))\d{2}(?!\d)")
CURRENCY_DECIMAL = re.compile(r"\b(?:RM|MYR)\b", re.IGNORECASE)
CURRENCY_IDR = re.compile(r"\b(?:Rp|IDR)\b", re.IGNORECASE)


def read_box(path):
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = raw.split(",", 8)
        if len(parts) == 9 and parts[8].strip():
            lines.append(parts[8].strip())
    return "\n".join(lines)


def parse_total(value):
    cleaned = re.sub(r"[^\d.]", "", value or "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def decimal_share(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    return sum(1 for line in lines if DECIMAL_AMOUNT.search(line)) / len(lines)


def detect_locale(text):
    if not text:
        return "idr"
    if CURRENCY_DECIMAL.search(text) and not CURRENCY_IDR.search(text):
        return "decimal"
    has_idr_group = IDR_GROUP.search(text) is not None
    has_small_decimal = SMALL_DECIMAL.search(text) is not None
    has_comma_cents = COMMA_CENTS.search(text) is not None
    if not has_idr_group and (has_small_decimal or has_comma_cents):
        return "decimal"
    return "idr"


def alarm_index(values, baseline, window=20, z=4.0, min_sd=0.1):
    mu = sum(baseline) / len(baseline)
    variance = sum((v - mu) ** 2 for v in baseline) / max(len(baseline) - 1, 1)
    limit = z * max(variance**0.5, min_sd) / window**0.5
    recent = deque(maxlen=window)
    for i, value in enumerate(values):
        recent.append(value)
        if len(recent) == window and abs(sum(recent) / window - mu) > limit:
            return i
    return None


def evaluate_alarm(baseline, before, after, window=20, z=4.0, min_sd=0.1):
    false_alarm = alarm_index(before, baseline, window, z, min_sd) is not None
    index = alarm_index(after, baseline, window, z, min_sd)
    return {"false_alarm": false_alarm, "delay": None if index is None else index + 1}

CORD_REJECTION_RATE = 0.19
CORD_DECIMAL_SHARE = 0.0


class DriftWindow:
    def __init__(self, window=20, z=4.0, min_sd=0.1):
        self.window = window
        self.z = z
        self.min_sd = min_sd
        self.rejections = deque(maxlen=window)
        self.decimals = deque(maxlen=window)
        self.alarmed = False
        self.lock = threading.Lock()

    def limit(self):
        return self.z * self.min_sd / self.window**0.5

    def observe(self, text, rejected):
        with self.lock:
            if self.alarmed:
                return True
            self.rejections.append(1.0 if rejected else 0.0)
            self.decimals.append(decimal_share(text))
            if len(self.rejections) < self.window:
                return False
            rejection_shift = abs(sum(self.rejections) / self.window - CORD_REJECTION_RATE)
            decimal_shift = abs(sum(self.decimals) / self.window - CORD_DECIMAL_SHARE)
            if rejection_shift > self.limit() or decimal_shift > self.limit():
                self.alarmed = True
            return self.alarmed