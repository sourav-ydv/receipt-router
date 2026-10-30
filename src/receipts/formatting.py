import json

INSTRUCTION = "Extract the receipt fields as JSON."
INSTRUCTION_IDR = (
    "Extract the receipt fields as JSON. "
    "A dot or comma in these amounts is a thousands separator: 12.500 means 12500."
)
INSTRUCTION_DECIMAL = (
    "Extract the receipt fields as JSON. "
    "A separator followed by exactly two digits is the decimal point: 9.00 means 9."
)
AMOUNT_FIELDS = ("subtotal", "discount", "service", "tax", "total")


def instruction_for(locale):
    if locale is None:
        return INSTRUCTION
    if locale == "idr":
        return INSTRUCTION_IDR
    if locale == "decimal":
        return INSTRUCTION_DECIMAL
    raise ValueError(f"unknown locale: {locale}")


def clean(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def compact(receipt):
    data = receipt.model_dump()
    data["items"] = [{k: clean(v) for k, v in item.items()} for item in data["items"]]
    for field in AMOUNT_FIELDS:
        data[field] = clean(data[field])
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def make_example(text, receipt, locale=None):
    return {
        "messages": [
            {"role": "system", "content": instruction_for(locale)},
            {"role": "user", "content": text},
            {"role": "assistant", "content": compact(receipt)},
        ]
    }