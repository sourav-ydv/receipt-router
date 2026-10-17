import json

INSTRUCTION = "Extract the receipt fields as JSON."
AMOUNT_FIELDS = ("subtotal", "discount", "service", "tax", "total")


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


def make_example(text, receipt):
    return {
        "messages": [
            {"role": "system", "content": INSTRUCTION},
            {"role": "user", "content": text},
            {"role": "assistant", "content": compact(receipt)},
        ]
    }