import pandas as pd
import pytest

from app.core.compensation import apply_spillover_compensation, compensation_status, event_view, parse_spillover
from app.models.sample import SampleRecord


def test_parse_and_apply_spillover_preserves_raw_events():
    events = pd.DataFrame(
        {
            "FSC-A": [1.0, 2.0],
            "FL1-A": [100.0, 200.0],
            "FL2-A": [50.0, 80.0],
        }
    )
    spill = parse_spillover({"$SPILL": "2,FL1-A,FL2-A,1,0.1,0.2,1"})

    compensated, warnings = apply_spillover_compensation(events, spill)

    assert warnings == []
    assert compensated is not None
    assert events["FL1-A"].tolist() == [100.0, 200.0]
    assert compensated["FSC-A"].tolist() == [1.0, 2.0]
    assert compensated["FL1-A"].iloc[0] != pytest.approx(events["FL1-A"].iloc[0])


def test_spillover_missing_channel_is_not_applied():
    events = pd.DataFrame({"FL1-A": [100.0]})
    spill = parse_spillover({"$SPILLOVER": "2,FL1-A,FL2-A,1,0.1,0.2,1"})

    compensated, warnings = apply_spillover_compensation(events, spill)

    assert compensated is None
    assert "missing" in warnings[0].lower()


def test_numeric_spillover_labels_resolve_to_pnn_order():
    events = pd.DataFrame(
        {
            "FSC-A": [1.0],
            "SSC-A": [2.0],
            "FL1-A": [100.0],
            "FL2-A": [50.0],
        }
    )
    spill = parse_spillover({"$SPILL": "2,3,4,1,0.1,0.2,1"})

    compensated, warnings = apply_spillover_compensation(events, spill)

    assert warnings == []
    assert compensated is not None
    assert compensated["FSC-A"].iloc[0] == 1.0
    assert compensated["FL1-A"].iloc[0] != events["FL1-A"].iloc[0]


def test_event_view_uses_compensated_when_requested():
    raw = pd.DataFrame({"FL1-A": [1.0]})
    compensated = pd.DataFrame({"FL1-A": [2.0]})
    spill = parse_spillover({"$SPILL": "1,FL1-A,1"})
    sample = SampleRecord("s1", "s1.fcs", path="unused.fcs", file_type="fcs", events=raw, spillover=spill, compensated_events=compensated)

    assert event_view(sample, False).equals(raw)
    assert event_view(sample, True).equals(compensated)
    assert "available" in compensation_status(sample)
