import sys

from receipts.config import PROCESSED_DIR, TEACHER_DIR
from receipts.data import read_jsonl


def main():
    split, index = sys.argv[1], int(sys.argv[2])
    gold = read_jsonl(PROCESSED_DIR / f"{split}.jsonl")[index]
    teacher = next(r for r in read_jsonl(TEACHER_DIR / f"{split}.jsonl") if r["id"] == index)
    print(gold["text"])
    print("-" * 40)
    print("gold:   ", gold["label"])
    print("teacher:", teacher["label"])
    print("problems:", teacher["problems"])


if __name__ == "__main__":
    main()