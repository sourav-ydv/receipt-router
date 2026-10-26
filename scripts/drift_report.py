from collections import Counter

from receipts.config import DATA_DIR, PROCESSED_DIR
from receipts.data import read_jsonl
from receipts.drift import decimal_share, evaluate_alarm
from receipts.validators import check, parse_receipt


def judge(row):
    receipt = parse_receipt(row["raw"])
    problems = ["unparseable"] if receipt is None else check(receipt)
    total = receipt.total if receipt else None
    gold = row["gold"]
    if total is None:
        kind = "missing"
    elif abs(total - gold) <= row["tolerance"]:
        kind = "right"
    elif abs(total - gold * 100) <= 1:
        kind = "times_100"
    else:
        kind = "other"
    return {"rejected": bool(problems), "kind": kind, "text": row["text"]}


def cord_rows():
    test = read_jsonl(PROCESSED_DIR / "test.jsonl")
    usable = [i for i, row in enumerate(test) if row["usable"]]
    predictions = read_jsonl(DATA_DIR / "student" / "predictions_q5_k_m.jsonl")
    rows = []
    for i, prediction in zip(usable, predictions):
        gold = test[i]["label"]["total"]
        if gold is not None:
            rows.append({"text": test[i]["text"], "gold": gold, "raw": prediction["raw"], "tolerance": 1.0})
    return rows


def sroie_rows():
    receipts = {r["id"]: r for r in read_jsonl(DATA_DIR / "sroie" / "receipts.jsonl")}
    predictions = read_jsonl(DATA_DIR / "sroie" / "predictions.jsonl")
    return [
        {
            "text": receipts[p["id"]]["text"],
            "gold": receipts[p["id"]]["total"],
            "raw": p["raw"],
            "tolerance": 0.006,
        }
        for p in predictions
    ]


def summarize(name, judged):
    n = len(judged)
    kinds = Counter(j["kind"] for j in judged)
    accepted = [j for j in judged if not j["rejected"]]
    wrong_accepted = [j for j in accepted if j["kind"] != "right"]
    print(f"{name} ({n} receipts)")
    print(f"  total correct        {kinds['right'] / n:.1%}")
    print(f"  total off by x100    {kinds['times_100'] / n:.1%}")
    print(f"  total otherwise wrong or missing  {(kinds['other'] + kinds['missing']) / n:.1%}")
    print(f"  rejected by validators  {1 - len(accepted) / n:.1%}")
    if accepted:
        print(f"  accepted but wrong total  {len(wrong_accepted)} of {len(accepted)} accepted")
    print()


def main():
    cord = [judge(r) for r in cord_rows()]
    sroie = [judge(r) for r in sroie_rows()]
    summarize("CORD test, the training domain", cord)
    summarize("SROIE, a different kind of receipt", sroie)

    half = len(cord) // 2
    features = {
        "validator rejection rate": lambda j: float(j["rejected"]),
        "share of lines with two-digit decimals": lambda j: decimal_share(j["text"]),
    }
    print("monitors, baseline = first half of CORD, window 20")
    for name, extract in features.items():
        baseline = [extract(j) for j in cord[:half]]
        before = [extract(j) for j in cord[half:]]
        after = [extract(j) for j in sroie]
        result = evaluate_alarm(baseline, before, after)
        delay = result["delay"]
        text = f"caught after {delay} SROIE receipts" if delay else "not caught"
        print(f"  {name}: false alarm on CORD {'yes' if result['false_alarm'] else 'no'}, {text}")


if __name__ == "__main__":
    main()
