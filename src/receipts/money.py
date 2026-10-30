import re

from .parsing import to_number

NUMBER = re.compile(r"[+-]?(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{2})?")
LOCALES = ("idr", "decimal")


def iter_numbers(text):
    for match in NUMBER.finditer(text or ""):
        start = match.start()
        raw = match.group(0)
        if start > 0 and text[start - 1] in "0123456789.,":
            continue
        if raw[:1] in "+-" and start > 0 and text[start - 1].isalnum():
            continue
        if (
            start >= 2
            and text[start - 1] == "-"
            and text[start - 2].isalnum()
            and raw[:1] not in "+-"
        ):
            continue
        yield raw


def parse_decimal(token):
    stripped = token.strip()
    sign = -1.0 if stripped.startswith("-") else 1.0
    body = stripped[1:] if stripped[:1] in "+-" else stripped
    match = re.fullmatch(r"(.+)[.,](\d{2})", body)
    if match:
        whole = re.sub(r"[.,]", "", match.group(1))
        if not whole:
            return None
        return sign * float(f"{whole}.{match.group(2)}")
    digits = re.sub(r"\D", "", body)
    if not digits:
        return None
    return sign * float(digits)


def money_tokens(text, locale):
    if locale not in LOCALES:
        raise ValueError(f"unknown locale: {locale}")
    parser = to_number if locale == "idr" else parse_decimal
    values = []
    for raw in iter_numbers(text):
        number = parser(raw)
        if number is not None:
            values.append(abs(number))
    return values