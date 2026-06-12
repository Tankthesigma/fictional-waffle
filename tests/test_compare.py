import math

import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.compare import batch_gate_statistics_table, compare_control_treated, comparison_insights, comparison_summary, fluorescence_median_table
from app.core.gating import rectangle_gate
from app.core.plotting import comparison_delta_chart
from app.models.sample import SampleRecord
from app.ui.callbacks_compare import _condition_groups, _default_groups


def _sample(sample_id: str, condition: str, values: list[float]) -> SampleRecord:
    frame = pd.DataFrame({"FITC-A": values})
    sample = SampleRecord(sample_id, f"{sample_id}.csv", path="unused.csv", file_type="csv", events=frame)
    sample.condition = condition
    sample.channels = summarize_channels(frame)
    return sample


def test_compare_includes_marker_aware_channel_label():
    control = _sample("c1", "control", [10, 10, 10])
    treated = _sample("t1", "treated", [20, 20, 20])
    control.channels[0].marker = "CD3"
    control.channels[0].fluorochrome = "FITC"

    row = compare_control_treated([control, treated], "control", "treated")[0].to_dict()

    assert row["channel"] == "FITC-A"
    assert row["channel_label"] == "CD3 FITC (FITC-A)"


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


def test_batch_gate_statistics_table_applies_gates_across_samples():
    control = _sample("c1", "control", [10, 20, 30])
    treated = _sample("t1", "treated", [40, 50, 60])
    for sample in (control, treated):
        sample.events["SSC-A"] = [1, 2, 3]
        sample.channels = summarize_channels(sample.events)
    gate = rectangle_gate("g1", "all", "FITC-A", "SSC-A", 0, 100, 0, 5)

    rows = batch_gate_statistics_table([control, treated], [gate])

    assert [row["sample_id"] for row in rows] == ["c1", "t1"]
    assert all(row["gate_name"] == "all" for row in rows)
    assert all(row["event_count"] == 3 for row in rows)


def test_comparison_summary_highlights_direction_and_guardrails():
    rows = [
        {
            "channel": "FITC-A",
            "median_difference": 15.0,
            "notes": "exploratory only",
        },
        {
            "channel": "PE-A",
            "median_difference": -4.0,
            "notes": "exploratory only; fold-change not computed for negative or near-zero medians; use median difference",
        },
        {
            "channel": "APC-A",
            "median_difference": 1.0,
            "notes": "exploratory only; replicate count is too low for inferential statistics",
        },
    ]

    summary = comparison_summary(rows)

    assert summary[0]["value"] == 3
    assert summary[1]["value"] == "+15"
    assert summary[1]["detail"] == "FITC-A median difference; exploratory only"
    assert summary[2]["value"] == "-4"
    assert summary[3]["value"] == 1
    assert summary[4]["value"] == 1


def test_comparison_insights_describe_shifts_and_guardrails_without_overclaiming():
    rows = [
        {
            "channel": "FITC-A",
            "median_difference": 15.0,
            "notes": "exploratory only",
        },
        {
            "channel": "PE-A",
            "median_difference": -4.0,
            "notes": "exploratory only; fold-change not computed for negative or near-zero medians; use median difference",
        },
        {
            "channel": "APC-A",
            "median_difference": 1.0,
            "notes": "exploratory only; replicate count is too low for inferential statistics",
        },
    ]

    insights = comparison_insights(rows, "control", "treated")
    text = " ".join(f"{item['title']} {item['message']} {item['detail']}" for item in insights)

    assert insights[0]["title"] == "Comparison Scope"
    assert "between control and treated" in insights[0]["message"]
    assert "FITC-A is higher in treated medians by +15" in text
    assert "2 channel(s) higher and 1 channel(s) lower" in text
    assert any(item["severity"] == "warning" and item["title"] == "Guarded Fold-Changes" for item in insights)
    assert any(item["severity"] == "warning" and item["title"] == "Low Replicate Review" for item in insights)
    assert "significant" not in text.lower()
    assert "diagnos" not in text.lower()


def test_comparison_insights_empty_state_is_waiting():
    insights = comparison_insights([])

    assert insights == [
        {
            "severity": "waiting",
            "title": "Choose Groups",
            "message": "Select control and treated groups to generate exploratory comparison notes.",
            "detail": "No statistical or biological interpretation is made automatically.",
        }
    ]


def test_comparison_delta_chart_plots_directional_median_shifts():
    rows = [
        {
            "channel": "FITC-A",
            "channel_label": "CD3 FITC (FITC-A)",
            "median_difference": 15.0,
            "notes": "exploratory only",
        },
        {
            "channel": "PE-A",
            "median_difference": -4.0,
            "notes": "exploratory only; fold-change not computed for negative or near-zero medians",
        },
    ]

    fig = comparison_delta_chart(rows)

    assert len(fig.data) == 1
    assert fig.data[0].type == "bar"
    assert list(fig.data[0].y) == ["CD3 FITC (FITC-A)", "PE-A"]
    assert list(fig.data[0].x) == [15.0, -4.0]
    assert fig.data[0].customdata[0][0] == "FITC-A"
    assert fig.layout.xaxis.title.text == "Treated median - control median"
    assert "guarded fold-change rows: 1" in fig.layout.annotations[0].text


def test_comparison_delta_chart_empty_state_is_friendly():
    fig = comparison_delta_chart([])

    assert fig.layout.annotations[0].text == "Choose control and treated groups to plot exploratory median differences."


def test_compare_group_defaults_choose_control_and_treated_conditions():
    samples = [
        _sample("c1", "control", [1, 2, 3]),
        _sample("t1", "treated", [4, 5, 6]),
        _sample("v1", "vehicle", [1, 2, 3]),
    ]

    groups = _condition_groups(samples)
    control, treated = _default_groups(groups)

    assert groups == ["control", "treated", "vehicle"]
    assert control == "control"
    assert treated == "treated"


def test_compare_group_defaults_fall_back_to_distinct_groups():
    control, treated = _default_groups(["day0", "day7"])

    assert control == "day0"
    assert treated == "day7"
