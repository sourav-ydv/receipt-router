from collections import Counter

from receipts.config import PROCESSED_DIR
from receipts.data import read_jsonl
from receipts.schema import Receipt
from receipts.validators import check


def main():
    rows = read_jsonl(PROCESSED_DIR / "train.jsonl")
    failures = Counter()
    clean = 0
    for row in rows:
        problems = check(Receipt(**row["label"]))
        failures.update(problems)
        if not problems:
            clean += 1
    print(f"{clean}/{len(rows)} gold receipts pass every rule")
    for rule, count in failures.most_common():
        print(f"{rule}: {count}")


if __name__ == "__main__":
    main()
