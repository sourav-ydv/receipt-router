from receipts.config import ROOT, PROCESSED_DIR, TEACHER_DIR
from receipts.data import read_jsonl, write_jsonl
from receipts.schema import Receipt
from receipts.validators import check


def main():
    rows = read_jsonl(PROCESSED_DIR / "train.jsonl")
    pool = []
    for record in read_jsonl(TEACHER_DIR / "train.jsonl"):
        label = record["label"]
        ok = bool(label) and not check(Receipt(**label))
        pool.append(
            {
                "id": record["id"],
                "text": rows[record["id"]]["text"],
                "label": label,
                "ok": ok,
            }
        )
    out_path = ROOT / "kaggle_upload" / "train_pool.jsonl"
    write_jsonl(pool, out_path)
    print(f"{len(pool)} labeled receipts, {sum(p['ok'] for p in pool)} pass the validators")
    print(out_path)


if __name__ == "__main__":
    main()
