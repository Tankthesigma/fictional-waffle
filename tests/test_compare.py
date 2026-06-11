import math

import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.compare import compare_control_treated, fluorescence_median_table
from app.models.sample import SampleRecord


def _sample(sample_id: str, condition: str, values: list[float]) -> SampleRecord:
    frame = pd.DataFrame({"FITC-A": values})
    sample = SampleRecord(sample_id, f"{sample_id}.csv", path="unused.csv", file_type="csv", events=frame)
    sample.condition = condition
    sample.channels = summarize_channels(frame)
    return sample


def test_compare_does_not_compute_fold_change_for_negative_medians():
    control = _sample("c1", "control", [-20, -20, -20])
    treated = _sample("t1", "treated", [-5, -5, -5])

    row = compare_control_treated([control, treated], "control", "treated")[0]

    assert row.median_difference == 15
    assert row.fold_change is None
    assert any("negative or near-zero medians" in note for note in row.notes)


def test_compare_does_not_compute_fold_change_for_near_zero_control():
    control = _sample("c1", "control", [1e-12, 1e-12, 1e-12])
    treated = _sample("t1", "treated", [1, 1, 1])

    row = compare_control_treated([control, treated], "control", "treated")[0]

    assert row.median_difference == 0.999999999999
    assert row.fold_change is None


def test_compare_keeps_fold_change_for_positive_medians():
    control = _sample("c1", "control", [10, 10, 10])
    treated = _sample("t1", "treated", [20, 20, 20])

    row = compare_control_treated([control, treated], "control", "treated")[0]

    assert row.fold_change == 2.0


def test_fluorescence_median_table_uses_none_not_nan_for_empty_values():
    sample = _sample("s1", "control", [math.nan, math.nan])

    row = fluorescence_median_table([sample])[0]

    assert row["FITC-A"] is None
