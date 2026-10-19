import pytest

from receipts.feedback import choose_additions, split_stream


def test_every_receipt_lands_in_exactly_one_place():
    start, chunks = split_stream(range(103), initial=20, rounds=4, seed=1)
    seen = start + [i for chunk in chunks for i in chunk]
    assert sorted(seen) == list(range(103))
    assert len(start) == 20
    assert len(chunks) == 4


def test_split_is_repeatable_and_depends_on_the_seed():
    assert split_stream(range(50), 10, 2, seed=3) == split_stream(range(50), 10, 2, seed=3)
    assert split_stream(range(50), 10, 2, seed=3) != split_stream(range(50), 10, 2, seed=4)


def test_escalation_arm_keeps_only_failed_receipts_with_a_good_label():
    chunk = [1, 2, 3, 4, 5]
    added = choose_additions("escalation", chunk, failed=[2, 4, 5], ok_ids=[1, 2, 4], seed=0)
    assert added == [2, 4]


def test_random_arm_adds_the_same_number_from_the_same_chunk():
    chunk = list(range(20))
    ok_ids = list(range(20))
    failed = [0, 1, 2, 3]
    added = choose_additions("random", chunk, failed, ok_ids, seed=5)
    assert len(added) == 4
    assert set(added) <= set(chunk)
    assert len(set(added)) == 4


def test_random_arm_never_adds_a_receipt_without_a_good_label():
    chunk = list(range(10))
    added = choose_additions("random", chunk, failed=[0, 1, 2], ok_ids=[0, 5, 6], seed=2)
    assert set(added) <= {0, 5, 6}


def test_random_arm_is_capped_by_the_available_good_labels():
    added = choose_additions("random", [1, 2, 3], failed=[1, 2, 3], ok_ids=[1], seed=0)
    assert added == [1]


def test_unknown_arm_is_rejected():
    with pytest.raises(ValueError):
        choose_additions("greedy", [1], [1], [1], seed=0)
