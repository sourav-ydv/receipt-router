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

    names = [
        n
        for n in ("filtered", "all", "q8_0", "q5_k_m", "q4_k_m")
        if (DATA_DIR / "student" / f"predictions_{n}.jsonl").exists()
    ]
    students = {}
    for name in names:
        rows = read_jsonl(DATA_DIR / "student" / f"predictions_{name}.jsonl")
        students[name] = dict(zip(usable, rows))

    gold = {i: Receipt(**test[i]["label"]) for i in ids}
    systems = {
        "teacher": [judge(Receipt(**teacher[i]["label"]) if teacher[i]["label"] else None, gold[i]) for i in ids],
    }
    for name in names:
        systems[f"student {name}"] = [judge(parse_receipt(students[name][i]["raw"]), gold[i]) for i in ids]

    print(f"{len(ids)} test receipts\n")
    for name, results in systems.items():
        summary(name, results)

    print()
    difference("filtered - teacher", systems["student filtered"], systems["teacher"])
    difference("filtered - all", systems["student filtered"], systems["student all"])
    for name in names:
        if name not in ("filtered", "all"):
            difference(f"{name} - filtered", systems[f"student {name}"], systems["student filtered"])

    total_tokens = sum(teacher[i]["tokens"] for i in ids)
    print("\nrouter: student first, teacher when the validators reject the student")
    for name in names:
        if name == "all":
            continue
        routed = []
        api_tokens = 0
        escalated = 0
        for k, i in enumerate(ids):
            student_result, problems = systems[f"student {name}"][k]
            if problems:
                routed.append(systems["teacher"][k])
                api_tokens += teacher[i]["tokens"]
                escalated += 1
            else:
                routed.append((student_result, problems))
        summary(f"router {name}", routed)
        print(f"{'':18} escalated {escalated} of {len(ids)}, API tokens {api_tokens / total_tokens:.0%}")
        difference(f"router {name} - teacher", routed, systems["teacher"])


if __name__ == "__main__":
    main()