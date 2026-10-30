import random

from receipts.config import DATA_DIR
from receipts.data import read_jsonl, write_jsonl
from receipts.drift import detect_locale
from receipts.formatting import instruction_for, make_example
from receipts.schema import Receipt
from receipts.validators import check


def rewrite(examples, locale):
    instruction = instruction_for(locale)
    rewritten = []
    for example in examples:
        example["messages"][0]["content"] = instruction
        rewritten.append(example)
    return rewritten


def decimal_examples():
    texts = {row["id"]: row["text"] for row in read_jsonl(DATA_DIR / "sroie" / "train_pool.jsonl")}
    kept = []
    skipped = 0
    for record in read_jsonl(DATA_DIR / "sroie" / "teacher_train.jsonl"):
        if record["problems"] or not record["label"]:
            skipped += 1
            continue
        text = texts[record["id"]]
        receipt = Receipt(**record["label"])
        if check(receipt, text=text):
            skipped += 1
            continue
        kept.append(make_example(text, receipt, locale=detect_locale(text)))
    return kept, skipped


def main():
    cord_path = DATA_DIR / "sft" / "train_filtered.jsonl"
    if not cord_path.exists():
        raise SystemExit(f"missing {cord_path}")
    cord = rewrite(read_jsonl(cord_path), "idr")
    extra, skipped = decimal_examples()
    mixed = cord + extra
    random.Random(42).shuffle(mixed)
    out_path = DATA_DIR / "sft" / "train_mixed.jsonl"
    write_jsonl(mixed, out_path)
    print(f"{len(cord)} CORD examples, {len(extra)} new examples, {skipped} skipped")
    print(f"wrote {len(mixed)} examples to {out_path}")

    val_path = DATA_DIR / "sft" / "validation_filtered.jsonl"
    if val_path.exists():
        validation = rewrite(read_jsonl(val_path), "idr")
        val_out = DATA_DIR / "sft" / "validation_idr.jsonl"
        write_jsonl(validation, val_out)
        print(f"wrote {len(validation)} validation examples to {val_out}")


if __name__ == "__main__":
    main()