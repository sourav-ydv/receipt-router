import sys
from collections import Counter

from receipts.config import PROCESSED_DIR, TEACHER_DIR
from receipts.data import read_jsonl
from receipts.schema import Receipt

FIELDS = ("subtotal", "discount", "service", "tax", "total")


def field_outcome(pred, gold):
    if pred == gold:
        return "match"
    if pred is None:
        return "teacher_null"
    if gold is None:
        return "gold_null"
    return "wrong"


def numbers(item):
    return (item.quantity, item.price, item.discount)


def same_name(a, b):
    return a.name.strip().lower() == b.name.strip().lower()


def compare_items(pred, gold):
    counts = Counter()
    examples = {"name_differs": [], "numbers_differ": [], "missing": []}
    left = list(pred.items)
    for g in gold.items:
        exact = next((p for p in left if same_name(p, g) and numbers(p) == numbers(g)), None)
        if exact:
            counts["exact"] += 1
            left.remove(exact)
            continue
        by_numbers = next((p for p in left if numbers(p) == numbers(g)), None)
        if by_numbers:
            counts["name_differs"] += 1
            examples["name_differs"].append((g.name, by_numbers.name))
            left.remove(by_numbers)
            continue
        by_name = next((p for p in left if same_name(p, g)), None)
        if by_name:
            counts["numbers_differ"] += 1
            examples["numbers_differ"].append((g.name, numbers(g), numbers(by_name)))
            left.remove(by_name)
            continue
        counts["missing"] += 1
        examples["missing"].append(g.name)
    counts["extra"] += len(left)
    counts["empty_names"] += sum(1 for p in pred.items if not p.name.strip())
    return counts, examples


def main():
    split = sys.argv[1]
    gold_rows = read_jsonl(PROCESSED_DIR / f"{split}.jsonl")
    teacher_rows = read_jsonl(TEACHER_DIR / f"{split}.jsonl")
    fields = {name: Counter() for name in FIELDS}
    items = Counter()
    examples = {"name_differs": [], "numbers_differ": [], "missing": []}
    for record in teacher_rows:
        if not record["label"]:
            continue
        gold = Receipt(**gold_rows[record["id"]]["label"])
        pred = Receipt(**record["label"])
        for name in FIELDS:
            fields[name][field_outcome(getattr(pred, name), getattr(gold, name))] += 1
        counts, found = compare_items(pred, gold)
        items.update(counts)
        for kind, rows in found.items():
            examples[kind].extend(rows)
    for name, counts in fields.items():
        print(name, dict(counts))
    print("items", dict(items))
    for kind, rows in examples.items():
        print(f"\n{kind} (first 6 of {len(rows)})")
        for row in rows[:6]:
            print("  ", row)


if __name__ == "__main__":
    main()