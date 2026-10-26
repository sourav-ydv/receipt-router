import argparse
import json
from pathlib import Path

from receipts.data import read_jsonl
from receipts.server import resolve_model
from receipts.student import Student


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument("--limit", type=int, default=150)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.source))[: args.limit]
    target = Path(args.target)
    done = {r["id"] for r in read_jsonl(target)} if target.exists() else set()

    student = Student(resolve_model())
    student.load()
    with target.open("a", encoding="utf-8") as f:
        for n, row in enumerate(rows, 1):
            if row["id"] in done:
                continue
            raw, seconds, _ = student(row["text"])
            f.write(json.dumps({"id": row["id"], "raw": raw, "seconds": seconds}) + "\n")
            f.flush()
            print(f"{n}/{len(rows)} id={row['id']} {seconds:.1f}s")


if __name__ == "__main__":
    main()
