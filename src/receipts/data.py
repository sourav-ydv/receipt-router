import json

from datasets import load_dataset

from .config import DATASET_NAME
from .parsing import receipt_from_cord, text_from_cord


def load_split(split):
    dataset = load_dataset(DATASET_NAME, split=split)
    return dataset.remove_columns(["image"])


def convert(row):
    truth = json.loads(row["ground_truth"])
    receipt = receipt_from_cord(truth["gt_parse"])
    return {
        "text": text_from_cord(truth["valid_line"]),
        "label": receipt.model_dump(),
    }


def write_jsonl(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
