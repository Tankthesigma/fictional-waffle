import numpy as np
import pandas as pd

from app.core.gating import rectangle_gate
from app.core.stats import gate_statistics


def test_orphan_gate_percent_parent_is_not_computed_from_total():
    events = pd.DataFrame({"FSC-A": [1, 2, 3, 4, 5], "SSC-A": [1, 2, 3, 4, 5], "FL1-A": [10, 20, 30, 40, 50]})
    gate = rectangle_gate("child", "orphan", "FSC-A", "SSC-A", 1, 2, 1, 2, parent_id="missing-parent")
    masks = {"child": np.array([True, True, False, False, False])}

    rows = gate_statistics(events, [gate], masks, ["FL1-A"])

    assert rows[0]["parent_gate"] == "missing:missing-parent"
    assert rows[0]["parent_missing"] is True
    assert rows[0]["percent_total"] == 40.0
    assert rows[0]["percent_parent"] is None


def test_default_gate_statistics_only_include_fluorescence_channels():
    events = pd.DataFrame(
        {
            "FSC-A": [1, 2, 3],
            "SSC-A": [1, 2, 3],
            "Time": [0, 1, 2],
            "FL1-A": [10, 20, 30],
        }
    )
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 4, 0, 4)
    masks = {"g1": np.array([True, True, True])}

    rows = gate_statistics(events, [gate], masks)

    assert "FL1-A_median" in rows[0]
    assert "Time_median" not in rows[0]
    assert "FSC-A_median" not in rows[0]


def test_gate_statistics_include_marker_aware_channel_labels():
    events = pd.DataFrame({"FSC-A": [1, 2, 3], "SSC-A": [1, 2, 3], "FITC-A": [10, 20, 30]})
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 4, 0, 4)
    masks = {"g1": np.array([True, True, True])}

    rows = gate_statistics(
        events,
        [gate],
        masks,
        ["FITC-A"],
        {"FSC-A": "Forward Scatter Area (FSC-A)", "SSC-A": "Side Scatter Area (SSC-A)", "FITC-A": "CD3 FITC (FITC-A)"},
    )

    assert rows[0]["channel_labels"] == "Forward Scatter Area (FSC-A), Side Scatter Area (SSC-A)"
