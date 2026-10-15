import json

from datasets import load_dataset

from .config import DATASET_NAME
from .parsing import is_usable, receipt_from_cord, text_from_cord


def load_split(split):
    dataset = load_dataset(DATASET_NAME, split=split)
    return dataset.remove_columns(["image"])


def convert(row):
    truth = json.loads(row["ground_truth"])
    parsed = truth["gt_parse"]
    return {
        "text": text_from_cord(truth["valid_line"]),
        "label": receipt_from_cord(parsed).model_dump(),
        "usable": is_usable(parsed),
    }


def write_jsonl(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
