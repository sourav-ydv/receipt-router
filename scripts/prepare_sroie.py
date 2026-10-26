import json
import random

from receipts.config import DATA_DIR, ROOT
from receipts.data import write_jsonl
from receipts.drift import parse_total, read_box

MAX_CHARS = 6000


def main():
    base = ROOT / "external" / "sroie" / "data"
    rows = []
    skipped = 0
    for key_path in sorted((base / "key").glob("*.json")):
        box_path = base / "box" / f"{key_path.stem}.csv"
        if not box_path.exists():
            skipped += 1
            continue
        try:
            key = json.loads(key_path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            skipped += 1
            continue
        total = parse_total(key.get("total"))
        text = read_box(box_path)
        if total is None or not text or len(text) > MAX_CHARS:
            skipped += 1
            continue
        rows.append({"id": key_path.stem, "text": text, "total": total, "total_raw": key.get("total")})
    random.Random(42).shuffle(rows)
    out_path = DATA_DIR / "sroie" / "receipts.jsonl"
    write_jsonl(rows, out_path)
    print(f"{len(rows)} receipts written to {out_path}, {skipped} skipped")


if __name__ == "__main__":
    main()
