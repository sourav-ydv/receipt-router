import re

from pydantic import ValidationError

from .schema import Receipt

TOLERANCE = 1.0


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def parse_receipt(raw):
    try:
        return Receipt.model_validate_json(extract_json(raw))
    except ValidationError:
        return None


def expected_items_sum(receipt):
    if receipt.subtotal is not None:
        return receipt.subtotal
    if receipt.tax is None:
        return receipt.total
    return None


def check(receipt):
    failures = []
    if not receipt.items:
        failures.append("no_items")
    if receipt.total is None:
        failures.append("missing_total")

    target = expected_items_sum(receipt)
    if receipt.items and target is not None:
        if abs(sum(i.price for i in receipt.items) - target) > TOLERANCE:
            failures.append("items_vs_subtotal")

    if None not in (receipt.subtotal, receipt.tax, receipt.total):
        if abs(receipt.subtotal + receipt.tax - receipt.total) > TOLERANCE:
            failures.append("subtotal_tax_total")

    return failures
