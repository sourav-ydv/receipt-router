import re

from .schema import LineItem, Receipt


def to_number(value):
    if value is None:
        return None
    text = re.sub(r"(?<=\d{3})[.,]\d{1,2}(?!\d)\s*$", "", str(value))
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    sign = -1.0 if re.match(r"\s*-", text) else 1.0
    return sign * float(digits)


def magnitude(value):
    return abs(value) if value is not None else None


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_dict(value):
    return value if isinstance(value, dict) else {}


def amount(value):
    if isinstance(value, list):
        for part in value:
            number = to_number(part)
            if number is not None:
                return number
        return None
    return to_number(value)


def discount_amount(value):
    parts = [magnitude(to_number(p)) for p in as_list(value)]
    parts = [p for p in parts if p is not None]
    return sum(parts) if parts else None


def parse_quantity(value):
    if not isinstance(value, (str, int)):
        return 1
    match = re.match(r"\s*(\d+)\s*(?:[xX]|$)", str(value))
    return int(match.group(1)) if match else 1


def has_name(row):
    name = row.get("nm")
    return isinstance(name, str) and bool(name.strip())


def parse_items(menu):
    items = []
    for row in as_list(menu):
        row = as_dict(row)
        price = amount(row.get("price"))
        if not has_name(row) or price is None:
            continue
        items.append(
            LineItem(
                name=row["nm"].strip(),
                quantity=parse_quantity(row.get("cnt")),
                price=price,
                discount=discount_amount(row.get("discountprice")) or 0.0,
            )
        )
    return items


def receipt_from_cord(gt_parse):
    sub = as_dict(gt_parse.get("sub_total"))
    total = as_dict(gt_parse.get("total"))
    return Receipt(
        items=parse_items(gt_parse.get("menu")),
        subtotal=amount(sub.get("subtotal_price")),
        discount=discount_amount(sub.get("discount_price")),
        service=amount(sub.get("service_price")),
        tax=amount(sub.get("tax_price")),
        total=amount(total.get("total_price")),
    )


def is_usable(gt_parse):
    rows = [as_dict(r) for r in as_list(gt_parse.get("menu"))]
    if any(r.get("price") is not None and not has_name(r) for r in rows):
        return False
    if not parse_items(gt_parse.get("menu")):
        return False
    return amount(as_dict(gt_parse.get("total")).get("total_price")) is not None


def text_from_cord(valid_lines):
    lines = []
    for line in valid_lines:
        words = [w.get("text", "") for w in line.get("words", [])]
        text = " ".join(w for w in words if w)
        if text:
            lines.append(text)
    return "\n".join(lines)
