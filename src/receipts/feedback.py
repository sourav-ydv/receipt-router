import random

ARMS = ("escalation", "random")


def split_stream(ids, initial, rounds, seed):
    order = sorted(ids)
    random.Random(seed).shuffle(order)
    start = order[:initial]
    rest = order[initial:]
    size = len(rest) // rounds
    chunks = [rest[i * size:(i + 1) * size] for i in range(rounds)]
    chunks[-1].extend(rest[rounds * size:])
    return start, chunks


def choose_additions(arm, chunk, failed, ok_ids, seed):
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    ok = set(ok_ids)
    escalated = [i for i in failed if i in ok]
    if arm == "escalation":
        return escalated
    candidates = [i for i in chunk if i in ok]
    return random.Random(seed).sample(candidates, min(len(escalated), len(candidates)))
