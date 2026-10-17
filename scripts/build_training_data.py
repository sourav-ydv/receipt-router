import argparse

from receipts.config import DATA_DIR, PROCESSED_DIR, TEACHER_DIR
from receipts.data import read_jsonl, write_jsonl
from receipts.formatting import make_example
from receipts.schema import Receipt
from receipts.validators import check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("split")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    rows = read_jsonl(PROCESSED_DIR / f"{args.split}.jsonl")
    kept = []
    seen = 0
    for record in read_jsonl(TEACHER_DIR / f"{args.split}.jsonl"):
        if not record["label"]:
            continue
        seen += 1
        receipt = Receipt(**record["label"])
        if not args.all and check(receipt):
            continue
        kept.append(make_example(rows[record["id"]]["text"], receipt))

    name = "all" if args.all else "filtered"
    out_path = DATA_DIR / "sft" / f"{args.split}_{name}.jsonl"
    write_jsonl(kept, out_path)
    print(f"{len(kept)} of {seen} labeled receipts written to {out_path}")


if __name__ == "__main__":
    main()