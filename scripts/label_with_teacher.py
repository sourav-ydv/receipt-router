import argparse
import json
import time

from receipts.config import PROCESSED_DIR, TEACHER_DIR, TEACHER_PAUSE
from receipts.data import read_jsonl
from receipts.teacher import DailyLimit, label, make_client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("split")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    rows = read_jsonl(PROCESSED_DIR / f"{args.split}.jsonl")
    out_path = TEACHER_DIR / f"{args.split}.jsonl"
    done = {r["id"] for r in read_jsonl(out_path)} if out_path.exists() else set()
    todo = [(i, r) for i, r in enumerate(rows) if r["usable"] and i not in done]
    if args.limit:
        todo = todo[: args.limit]

    client = make_client()
    spent = 0
    TEACHER_DIR.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        for n, (i, row) in enumerate(todo, 1):
            try:
                raw, receipt, problems, tokens = label(client, row["text"])
            except DailyLimit as limit:
                print(f"daily limit reached, try again in about {limit.wait / 60:.0f} minutes")
                break
            if raw is None:
                print(f"{n}/{len(todo)} id={i} no response, will retry next run")
                continue
            record = {
                "id": i,
                "raw": raw,
                "label": receipt.model_dump() if receipt else None,
                "problems": problems,
                "tokens": tokens,
            }
            spent += tokens
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{n}/{len(todo)} id={i} {problems or 'ok'} tokens={tokens} spent={spent}")
            time.sleep(TEACHER_PAUSE)


if __name__ == "__main__":
    main()
