import re
from collections import deque

DECIMAL_AMOUNT = re.compile(r"\d[.,]\d{2}(?!\d)")


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
