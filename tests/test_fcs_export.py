from __future__ import annotations

import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.fcs_export import export_gated_population_csv, export_gated_population_fcs
from app.core.gating import rectangle_gate
from app.models.sample import SampleRecord


def _sample(tmp_path, compensated: bool = False) -> SampleRecord:
    events = pd.DataFrame({"FSC-A": [1.0, 2.0, 3.0, 4.0], "FL1-A": [10.0, 20.0, 30.0, 40.0]})
    sample = SampleRecord("s1", "source.fcs", tmp_path / "source.fcs", "fcs", events)
    sample.channels = summarize_channels(events, {})
    if compensated:
        sample.compensated_events = events.assign(FL1_A_COMP=[100.0, 200.0, 300.0, 400.0]).drop(columns=["FL1-A"]).rename(columns={"FL1_A_COMP": "FL1-A"})
    return sample


def test_export_gated_population_fcs_round_trips_with_metadata_and_ranges(tmp_path):
    from flowio import FlowData

    sample = _sample(tmp_path)
    gate = rectangle_gate("g1", "Target Gate", "FSC-A", "FL1-A", 1.5, 3.5, 0, 35)

    result = export_gated_population_fcs(sample, [gate], "g1", tmp_path)

    assert result.event_count == 2
    parsed = FlowData(str(result.path))
    assert parsed.event_count == 2
    assert [parsed.channels[1]["pnn"], parsed.channels[2]["pnn"]] == ["FSC-A", "FL1-A"]
    assert parsed.channels[1]["pnr"] >= 4
    assert parsed.channels[2]["pnr"] >= 32
    assert parsed.text["afw_export_type"] == "gated_population"
    assert parsed.text["afw_gate_id"] == "g1"
    assert parsed.text["afw_view"] == "raw"


def test_compensated_fcs_export_is_loudly_labeled_and_does_not_mutate_raw(tmp_path):
    from flowio import FlowData

    sample = _sample(tmp_path, compensated=True)
    raw_before = sample.events.copy(deep=True)
    gate = rectangle_gate("g1", "Comp Gate", "FSC-A", "FL1-A", 1.5, 4.5, 0, 450)
    gate.metadata["event_view"] = "metadata_compensated"

    result = export_gated_population_fcs(sample, [gate], "g1", tmp_path, use_compensation=True)

    assert "COMPENSATED" in result.path.name
    assert sample.events.equals(raw_before)
    parsed = FlowData(str(result.path))
    assert parsed.text["afw_compensated"] == "true"
    assert parsed.text["afw_view"] == "metadata_compensated"


def test_export_gated_population_csv_uses_selected_gate(tmp_path):
    sample = _sample(tmp_path)
    gate = rectangle_gate("g1", "CSV Gate", "FSC-A", "FL1-A", 2.5, 4.5, 0, 50)

    result = export_gated_population_csv(sample, [gate], "g1", tmp_path)

    exported = pd.read_csv(result.path)
    assert result.event_count == 2
    assert exported["FSC-A"].tolist() == [3.0, 4.0]
