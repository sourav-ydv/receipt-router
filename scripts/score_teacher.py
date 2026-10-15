import sys

from receipts.config import PROCESSED_DIR, TEACHER_DIR
from receipts.data import read_jsonl
from receipts.schema import Receipt
from receipts.scoring import score, summarize
from receipts.validators import check


def show(name, scores):
    summary = summarize(scores)
    cells = ", ".join(f"{key} {value:.1%}" for key, value in summary.items())
    print(f"{name} ({len(scores)}): {cells}")


def main():
    split = sys.argv[1]
    gold = read_jsonl(PROCESSED_DIR / f"{split}.jsonl")
    teacher = read_jsonl(TEACHER_DIR / f"{split}.jsonl")
    everything = []
    accepted = []
    for record in teacher:
        truth = Receipt(**gold[record["id"]]["label"])
        pred = Receipt(**record["label"]) if record["label"] else Receipt()
        result = score(pred, truth)
        everything.append(result)
        problems = check(pred) if record["label"] else ["unparseable"]
        if not problems:
            accepted.append(result)
    show("all teacher answers", everything)
    show("passed validators", accepted)


if __name__ == "__main__":
    main()
