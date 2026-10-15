from collections import Counter


def item_key(item):
    return (item.name.strip().lower(), item.quantity, item.price)


def items_f1(pred, gold):
    pred_items = Counter(item_key(i) for i in pred.items)
    gold_items = Counter(item_key(i) for i in gold.items)
    if not pred_items and not gold_items:
        return 1.0
    hits = sum((pred_items & gold_items).values())
    if hits == 0:
        return 0.0
    precision = hits / sum(pred_items.values())
    recall = hits / sum(gold_items.values())
    return 2 * precision * recall / (precision + recall)


def score(pred, gold):
    return {
        "total": pred.total == gold.total,
        "subtotal": pred.subtotal == gold.subtotal,
        "tax": pred.tax == gold.tax,
        "items_f1": items_f1(pred, gold),
        "exact": pred == gold,
    }


def summarize(scores):
    if not scores:
        return {}
    return {key: sum(float(s[key]) for s in scores) / len(scores) for key in scores[0]}
