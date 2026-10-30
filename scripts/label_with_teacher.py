import argparse
import json
import time
from collections import Counter
from pathlib import Path

from receipts.config import PROCESSED_DIR, TEACHER_DIR, TEACHER_PAUSE
from receipts.data import read_jsonl
from receipts.drift import detect_locale
from receipts.teacher import (
    DailyLimit,
    cord_tasks,
    file_tasks,
    label,
    make_client,
    remaining,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("split", nargs="?")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    if args.split and (args.input or args.output):
        parser.error("pass a split or --input and --output, not both")
    if bool(args.input) != bool(args.output):
        parser.error("--input and --output are used together")
    if not args.split and not args.input:
        parser.error("pass a split or --input and --output")
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.split:
        tasks = cord_tasks(read_jsonl(PROCESSED_DIR / f"{args.split}.jsonl"))
        out_path = TEACHER_DIR / f"{args.split}.jsonl"
        TEACHER_DIR.mkdir(parents=True, exist_ok=True)
    else:
        tasks = file_tasks(read_jsonl(args.input))
        out_path = args.output
        out_path.parent.mkdir(parents=True, exist_ok=True)

    done = {r["id"] for r in read_jsonl(out_path)} if out_path.exists() else set()
    todo = remaining(tasks, done, args.limit)
    counts = Counter(detect_locale(row["text"]) for row in todo)
    print(f"{len(todo)} to label, locales {dict(counts)}")
    if not todo:
        return

    client = make_client()
    spent = 0
    with out_path.open("a", encoding="utf-8") as f:
        for n, row in enumerate(todo, 1):
            try:
                raw, receipt, problems, tokens = label(client, row["text"])
            except DailyLimit as limit:
                print(f"daily limit reached, try again in about {limit.wait / 60:.0f} minutes")
                break
            if raw is None:
                print(f"{n}/{len(todo)} id={row['id']} no response, will retry next run")
                continue
            record = {
                "id": row["id"],
                "raw": raw,
                "label": receipt.model_dump() if receipt else None,
                "problems": problems,
                "tokens": tokens,
            }
            spent += tokens
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{n}/{len(todo)} id={row['id']} {problems or 'ok'} tokens={tokens} spent={spent}")
            time.sleep(TEACHER_PAUSE)


if __name__ == "__main__":
    main()