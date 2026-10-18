from receipts.stats import bootstrap_ci, paired_diff


def test_constant_values_give_a_zero_width_interval():
    assert bootstrap_ci([1.0] * 20) == (1.0, 1.0)


def test_interval_contains_the_mean():
    values = [1.0] * 6 + [0.0] * 4
    low, high = bootstrap_ci(values)
    assert low <= 0.6 <= high


def test_identical_series_have_zero_difference():
    mean, (low, high) = paired_diff([1.0, 0.0, 1.0], [1.0, 0.0, 1.0])
    assert mean == 0.0
    assert low == 0.0
    assert high == 0.0