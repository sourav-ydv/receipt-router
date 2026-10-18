from receipts.config import DATA_DIR, PROCESSED_DIR, TEACHER_DIR
from receipts.data import read_jsonl
from receipts.schema import Receipt
from receipts.scoring import score
from receipts.stats import bootstrap_ci, paired_diff
from receipts.validators import check, parse_receipt


def judge(pred, gold):
    problems = ["unparseable"] if pred is None else check(pred)
    return score(pred or Receipt(), gold), problems


def pct(value):
    return f"{value:.1%}"


def summary(name, results):
    exact = [float(r["exact"]) for r, _ in results]
    f1 = [r["items_f1"] for r, _ in results]
    accepted = [1.0 if not p else 0.0 for _, p in results]
    low, high = bootstrap_ci(exact)
    print(
        f"{name:18} exact {pct(sum(exact) / len(exact))} [{pct(low)}, {pct(high)}]"
        f"  items_f1 {pct(sum(f1) / len(f1))}  accepted {pct(sum(accepted) / len(accepted))}"
    )


def difference(name, a, b):
    mean, (low, high) = paired_diff(
        [float(r["exact"]) for r, _ in a], [float(r["exact"]) for r, _ in b]
    )
    print(f"{name:34} {mean * 100:+.1f} points [{low * 100:+.1f}, {high * 100:+.1f}]")


def main():
    test = read_jsonl(PROCESSED_DIR / "test.jsonl")
    usable = [i for i, row in enumerate(test) if row["usable"]]
    teacher = {r["id"]: r for r in read_jsonl(TEACHER_DIR / "test.jsonl")}
    ids = [i for i in usable if i in teacher]

    students = {}
    for name in ("filtered", "all"):
        rows = read_jsonl(DATA_DIR / "student" / f"predictions_{name}.jsonl")
        students[name] = dict(zip(usable, rows))

    gold = {i: Receipt(**test[i]["label"]) for i in ids}
    systems = {
        "teacher": [judge(Receipt(**teacher[i]["label"]) if teacher[i]["label"] else None, gold[i]) for i in ids],
        "student filtered": [judge(parse_receipt(students["filtered"][i]["raw"]), gold[i]) for i in ids],
        "student all": [judge(parse_receipt(students["all"][i]["raw"]), gold[i]) for i in ids],
    }

    print(f"{len(ids)} test receipts\n")
    for name, results in systems.items():
        summary(name, results)

    print()
    difference("filtered - teacher", systems["student filtered"], systems["teacher"])
    difference("filtered - all", systems["student filtered"], systems["student all"])
    difference("all - teacher", systems["student all"], systems["teacher"])

    routed = []
    escalated = 0
    api_tokens = 0
    total_tokens = sum(teacher[i]["tokens"] for i in ids)
    for k, i in enumerate(ids):
        student_result, problems = systems["student filtered"][k]
        if problems:
            routed.append(systems["teacher"][k])
            escalated += 1
            api_tokens += teacher[i]["tokens"]
        else:
            routed.append((student_result, problems))

    print()
    summary("router", routed)
    difference("router - teacher", routed, systems["teacher"])
    print(f"\nescalated to the API: {escalated} of {len(ids)} receipts")
    print(f"API tokens: {api_tokens} of {total_tokens} ({api_tokens / total_tokens:.0%})")


if __name__ == "__main__":
    main()