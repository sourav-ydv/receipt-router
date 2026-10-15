import json
import sys

from receipts.data import load_split
from receipts.parsing import receipt_from_cord
from receipts.validators import check


def main():
    rule = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    shown = 0
    for row in load_split("train"):
        parsed = json.loads(row["ground_truth"])["gt_parse"]
        if rule in check(receipt_from_cord(parsed)):
            print(json.dumps(parsed, ensure_ascii=False, indent=1))
            print("-" * 40)
            shown += 1
            if shown == limit:
                break


if __name__ == "__main__":
    main()