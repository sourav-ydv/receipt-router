import json
import sys
from pathlib import Path

from receipts.config import DATA_DIR
from receipts.stats import bootstrap_ci

FEEDBACK_DIR = DATA_DIR / "feedback"


def load():
    runs = {}
    for path in sorted(FEEDBACK_DIR.glob("feedback_*_seed*.json")):
        stem = path.stem.split("_")
        arm, seed = stem[1], int(stem[2].removeprefix("seed"))
        history = json.loads(path.read_text())
        if len(history) == 5:
            runs[(arm, seed)] = history
    return runs


def mean(values):
    return sum(values) / len(values)


def pct(value):
    return f"{value * 100:.1f}"


def curve_table(runs, key):
    arms = ("escalation", "random")
    seeds = sorted(
        s
        for s in {seed for _, seed in runs}
        if all((a, s) in runs and key in runs[(a, s)][0] for a in arms)
    )
    if not seeds:
        return
    print(f"{key}, mean over seeds {seeds}")
    print("round  " + "  ".join(f"{a:>10}" for a in arms) + "   difference")
    for r in range(5):
        cells = []
        for arm in arms:
            values = [runs[(arm, s)][r][key] for s in seeds if (arm, s) in runs]
            cells.append(mean(values))
        print(f"{r:>5}  " + "  ".join(f"{pct(c):>10}" for c in cells) + f"   {(cells[0] - cells[1]) * 100:+.1f}")
    print()


def per_receipt(runs, arm, round_number, seeds):
    flags = [runs[(arm, s)][round_number]["per_receipt_exact"] for s in seeds]
    return [mean(col) for col in zip(*flags)]


def paired(runs, round_numbers, seeds):
    diffs = []
    for r in round_numbers:
        esc = per_receipt(runs, "escalation", r, seeds)
        rnd = per_receipt(runs, "random", r, seeds)
        diffs.append([a - b for a, b in zip(esc, rnd)])
    return [mean(col) for col in zip(*diffs)]


def main():
    runs = load()
    if not runs:
        sys.exit(f"no finished runs in {FEEDBACK_DIR}")
    curve_table(runs, "test_exact")
    curve_table(runs, "both_exact")

    seeds = sorted({s for (_, s) in runs if all((a, s) in runs for a in ("escalation", "random"))})
    seeds = [s for s in seeds if "per_receipt_exact" in runs[("escalation", s)][-1]]
    if not seeds:
        return
    print(f"escalation minus random on {len(per_receipt(runs, 'random', 4, seeds))} test and validation receipts, seeds {seeds}")
    for label, rounds in (("final round", [4]), ("rounds 2 to 4", [2, 3, 4]), ("rounds 1 to 4", [1, 2, 3, 4])):
        diffs = paired(runs, rounds, seeds)
        low, high = bootstrap_ci(diffs)
        print(f"{label:15} {mean(diffs) * 100:+.1f} points [{low * 100:+.1f}, {high * 100:+.1f}]")
    print()

    print("train size and receipts added per round")
    for arm in ("escalation", "random"):
        for s in seeds:
            h = runs[(arm, s)]
            sizes = [r["train_size"] for r in h]
            added = sum(r.get("added", 0) for r in h)
            print(f"{arm:10} seed {s}: {sizes}, added {added}")

    if "--plot" in sys.argv:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6.5, 4))
        for arm, color in (("escalation", "tab:red"), ("random", "tab:gray")):
            ys, xs = [], []
            for r in range(5):
                values = [runs[(arm, s)][r]["both_exact"] for s in seeds]
                ys.append(mean(values) * 100)
                xs.append(mean([runs[(arm, s)][r]["train_size"] for s in seeds]))
            ax.plot(xs, ys, marker="o", label=arm, color=color)
        ax.set_xlabel("training receipts")
        ax.set_ylabel("exact match (%), test and validation")
        ax.legend()
        ax.grid(alpha=0.3)
        out = Path("docs")
        out.mkdir(exist_ok=True)
        fig.tight_layout()
        fig.savefig(out / "feedback_curve.png", dpi=150)
        print("saved docs/feedback_curve.png")


if __name__ == "__main__":
    main()
