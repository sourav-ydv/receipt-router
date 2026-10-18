import random

def bootstrap_ci(values, rounds=2000, seed=42):
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(rounds))
    return means[int(0.025 * rounds)], means[int(0.975 * rounds) - 1]

def paired_diff(a, b, rounds=2000, seed=42):
    diffs = [x - y for x, y in zip(a, b)]
    mean = sum(diffs) / len(diffs)
    return mean, bootstrap_ci(diffs, rounds, seed)