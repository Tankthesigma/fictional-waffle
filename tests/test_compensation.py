import pandas as pd
import pytest

from app.core.compensation import (
    apply_manual_spillover,
    apply_spillover_compensation,
    compensation_status,
    event_view,
    parse_spillover,
    spillover_from_matrix_rows,
    spillover_matrix_rows,
)
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


def test_spillover_matrix_rows_default_to_identity_for_fluorescence_channels():
    raw = pd.DataFrame({"FSC-A": [1.0], "FL1-A": [100.0], "FL2-A": [50.0]})
    sample = SampleRecord("s1", "s1.fcs", path="unused.fcs", file_type="fcs", events=raw)
    sample.channels = []
    sample.channels.append(type("Channel", (), {"raw_name": "FL1-A", "role": "fluorescence"})())
    sample.channels.append(type("Channel", (), {"raw_name": "FL2-A", "role": "fluorescence"})())

    rows = spillover_matrix_rows(sample)

    assert rows == [{"channel": "FL1-A", "FL1-A": 1.0, "FL2-A": 0.0}, {"channel": "FL2-A", "FL1-A": 0.0, "FL2-A": 1.0}]


def test_manual_spillover_matrix_applies_without_mutating_raw_events():
    raw = pd.DataFrame({"FL1-A": [100.0, 200.0], "FL2-A": [50.0, 80.0]})
    sample = SampleRecord("s1", "s1.fcs", path="unused.fcs", file_type="fcs", events=raw)
    rows = [{"channel": "FL1-A", "FL1-A": 1.0, "FL2-A": 0.1}, {"channel": "FL2-A", "FL1-A": 0.2, "FL2-A": 1.0}]

    warnings = apply_manual_spillover(sample, rows)

    assert warnings == []
    assert sample.compensated_events is not None
    assert sample.events["FL1-A"].tolist() == [100.0, 200.0]
    assert sample.compensated_events["FL1-A"].iloc[0] != sample.events["FL1-A"].iloc[0]


def test_spillover_from_matrix_rows_rejects_bad_values():
    rows = [{"channel": "FL1-A", "FL1-A": "nope"}]

    with pytest.raises(ValueError, match="must be numeric"):
        spillover_from_matrix_rows(rows)
