from receipts.config import PROCESSED_DIR
from receipts.data import convert, load_split, write_jsonl


def main():
    for split in ("train", "validation", "test"):
        dataset = load_split(split)
        rows = [convert(row) for row in dataset]
        write_jsonl(rows, PROCESSED_DIR / f"{split}.jsonl")
        print(split, len(rows))


if __name__ == "__main__":
    main()
