import statistics
from collections import Counter

from receipts.config import DATA_DIR
from receipts.data import read_jsonl
from receipts.validators import check, parse_receipt


def label_of(total, gold):
    if total is None:
        return "no total"
    if abs(total - gold) <= 0.006:
        return "right"
    for factor, name in ((100, "x100"), (1000, "x1000"), (10, "x10")):
        if abs(total - gold * factor) <= 1:
            return name
    return "other"


def main():
    receipts = {r["id"]: r for r in read_jsonl(DATA_DIR / "sroie" / "receipts.jsonl")}
    predictions = read_jsonl(DATA_DIR / "sroie" / "predictions.jsonl")
    counts = Counter()
    others = []
    for p in predictions:
        gold = receipts[p["id"]]["total"]
        receipt = parse_receipt(p["raw"])
        if receipt is None:
            counts["unparseable"] += 1
            continue
        label = label_of(receipt.total, gold)
        counts[label] += 1
        if label == "other":
            others.append((p["id"], gold, receipt.total, check(receipt)))

    print("what the student's total looks like next to the printed one")
    for label, count in counts.most_common():
        print(f"  {label:12} {count}")

    print("\nsome of the 'other' cases: id, printed total, student total, validator problems")
    for row in others[:12]:
        print("  ", row)

    seconds = sorted(p["seconds"] for p in predictions)
    p95 = seconds[int(0.95 * len(seconds)) - 1]
    print(f"\nseconds per receipt on this machine: median {statistics.median(seconds):.1f}, p95 {p95:.1f}, max {seconds[-1]:.1f}")


if __name__ == "__main__":
    main()