import re

from pydantic import ValidationError

from .drift import detect_locale
from .money import money_tokens
from .schema import Receipt

RELATIVE_TOLERANCE = 0.0005
MIN_TOLERANCE = 1.0
DECIMAL_TOLERANCE = 0.01
IDR_TOTAL_CAP = 1e11
DECIMAL_TOTAL_CAP = 1e9


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def parse_receipt(raw):
    try:
        return Receipt.model_validate_json(extract_json(raw))
    except ValidationError:
        return None


def tolerance(receipt, locale="idr"):
    base = receipt.total or receipt.subtotal or 0.0
    floor = DECIMAL_TOLERANCE if locale == "decimal" else MIN_TOLERANCE
    return max(floor, base * RELATIVE_TOLERANCE)


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


def total_matches(receipt, locale="idr"):
    if receipt.subtotal is None or receipt.total is None:
        return True
    base = receipt.subtotal - (receipt.discount or 0.0) + (receipt.service or 0.0)
    options = (base + (receipt.tax or 0.0), base)
    limit = tolerance(receipt, locale)
    return any(abs(o - receipt.total) <= limit for o in options)


def items_explain_total(receipt, locale="idr"):
    if receipt.subtotal is not None or receipt.tax is None or receipt.total is None or not receipt.items:
        return True
    limit = tolerance(receipt, locale)
    nets = [items_net(receipt)]
    if locale == "decimal":
        weighted = sum(item.quantity * (item.price - item.discount) for item in receipt.items)
        if weighted != nets[0]:
            nets.append(weighted)
    for net in nets:
        base = net - (receipt.discount or 0.0) + (receipt.service or 0.0)
        options = (base, base + receipt.tax)
        if any(abs(option - receipt.total) <= limit for option in options):
            return True
    return False


def printed_amounts(receipt):
    values = []
    for item in receipt.items:
        if item.price:
            values.append(item.price)
        if item.discount:
            values.append(item.discount)
    for name in ("subtotal", "discount", "service", "tax", "total"):
        value = getattr(receipt, name)
        if value:
            values.append(value)
    return values


def grounding_problems(receipt, text, locale):
    problems = []
    cap = DECIMAL_TOTAL_CAP if locale == "decimal" else IDR_TOTAL_CAP
    if receipt.total is not None and abs(receipt.total) > cap:
        problems.append("implausible_total")
    tokens = money_tokens(text, locale)
    limit = tolerance(receipt, locale)
    if any(
        not any(abs(value - token) <= limit for token in tokens)
        for value in printed_amounts(receipt)
    ):
        problems.append("ungrounded_amount")
    return problems


def check(receipt, text=None, locale=None):
    if locale is None and text is not None:
        locale = detect_locale(text)
    if locale is None:
        locale = "idr"

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
        limit = tolerance(receipt, locale)
        if not any(abs(net - t) <= limit for t in targets):
            failures.append("items_vs_subtotal")

    if not total_matches(receipt, locale):
        failures.append("subtotal_tax_total")

    if not items_explain_total(receipt, locale):
        failures.append("items_vs_subtotal")

    if text is not None:
        failures.extend(grounding_problems(receipt, text, locale))

    return failures