import re

from .schema import LineItem, Receipt


def to_number(value):
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    return float(digits)


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_dict(value):
    return value if isinstance(value, dict) else {}


def parse_items(menu):
    items = []
    for row in as_list(menu):
        row = as_dict(row)
        name = row.get("nm")
        price = to_number(row.get("price"))
        if not name or price is None:
            continue
        quantity = to_number(row.get("cnt"))
        items.append(
            LineItem(
                name=str(name).strip(),
                quantity=int(quantity) if quantity else 1,
                price=price,
            )
        )
    return items


def receipt_from_cord(gt_parse):
    sub = as_dict(gt_parse.get("sub_total"))
    total = as_dict(gt_parse.get("total"))
    return Receipt(
        items=parse_items(gt_parse.get("menu")),
        subtotal=to_number(sub.get("subtotal_price")),
        tax=to_number(sub.get("tax_price")),
        total=to_number(total.get("total_price")),
    )


def text_from_cord(valid_lines):
    lines = []
    for line in valid_lines:
        words = [w.get("text", "") for w in line.get("words", [])]
        text = " ".join(w for w in words if w)
        if text:
            lines.append(text)
    return "\n".join(lines)
