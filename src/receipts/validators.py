import re

from pydantic import ValidationError

from .schema import Receipt

RELATIVE_TOLERANCE = 0.0005
MIN_TOLERANCE = 1.0


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def parse_receipt(raw):
    try:
        return Receipt.model_validate_json(extract_json(raw))
    except ValidationError:
        return None


def tolerance(receipt):
    base = receipt.total or receipt.subtotal or 0.0
    return max(MIN_TOLERANCE, base * RELATIVE_TOLERANCE)


def items_net(receipt):
    return sum(i.price - i.discount for i in receipt.items)


def item_targets(receipt):
    if receipt.subtotal is not None:
        targets = [receipt.subtotal, receipt.total]
    elif receipt.tax is None:
        targets = [receipt.total]
    else:
        targets = []
    return [t for t in targets if t is not None]


def total_matches(receipt):
    if receipt.subtotal is None or receipt.total is None:
        return True
    base = receipt.subtotal - (receipt.discount or 0.0) + (receipt.service or 0.0)
    options = (base + (receipt.tax or 0.0), base)
    return any(abs(o - receipt.total) <= tolerance(receipt) for o in options)


def check(receipt):
    failures = []
    if not receipt.items:
        failures.append("no_items")
    if any(not item.name.strip() for item in receipt.items):
        failures.append("empty_item_name")
    if receipt.total is None:
        failures.append("missing_total")

    targets = item_targets(receipt)
    if receipt.items and targets:
        net = items_net(receipt)
        if not any(abs(net - t) <= tolerance(receipt) for t in targets):
            failures.append("items_vs_subtotal")

    if not total_matches(receipt):
        failures.append("subtotal_tax_total")

    return failures
