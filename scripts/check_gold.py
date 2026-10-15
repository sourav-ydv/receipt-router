from collections import Counter

from receipts.config import PROCESSED_DIR
from receipts.data import read_jsonl
from receipts.schema import Receipt
from receipts.validators import check


def main():
    rows = read_jsonl(PROCESSED_DIR / "train.jsonl")
    usable = [r for r in rows if r["usable"]]
    failures = Counter()
    clean = 0
    for row in usable:
        problems = check(Receipt(**row["label"]))
        failures.update(problems)
        if not problems:
            clean += 1
    print(f"{len(usable)}/{len(rows)} receipts are usable")
    print(f"{clean}/{len(usable)} usable receipts pass every rule")
    for rule, count in failures.most_common():
        print(f"{rule}: {count}")


if __name__ == "__main__":
    main()
