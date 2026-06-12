from __future__ import annotations

import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.concat import concatenate_samples, export_concatenated_fcs
from app.models.sample import SampleRecord


def _sample(tmp_path, sample_id: str, columns: list[str] | None = None) -> SampleRecord:
    columns = columns or ["FSC-A", "FL1-A"]
    events = pd.DataFrame({columns[0]: [1.0, 2.0], columns[1]: [10.0, 20.0]})
    sample = SampleRecord(sample_id, f"{sample_id}.fcs", tmp_path / f"{sample_id}.fcs", "fcs", events)
    sample.channels = summarize_channels(events, {})
    return sample


def test_concatenate_samples_adds_sample_index_and_mapping(tmp_path):
    result = concatenate_samples([_sample(tmp_path, "s1"), _sample(tmp_path, "s2")])

    assert result.sample is not None
    assert result.sample.event_count == 4
    assert result.sample.events["AFW_SAMPLE_INDEX"].tolist() == [1, 1, 2, 2]
    assert result.mapping_rows == [
        {"sample_index": 1, "sample_id": "s1", "filename": "s1.fcs", "event_count": 2},
        {"sample_index": 2, "sample_id": "s2", "filename": "s2.fcs", "event_count": 2},
    ]
    assert result.skipped == []


def test_concatenate_samples_skips_incompatible_channels(tmp_path):
    result = concatenate_samples([_sample(tmp_path, "s1"), _sample(tmp_path, "bad", ["FSC-A", "FL2-A"])])

    assert result.sample is not None
    assert result.sample.event_count == 2
    assert result.skipped == ["bad: channel order/name mismatch"]


def test_export_concatenated_fcs_writes_sidecar_mapping(tmp_path):
    from flowio import FlowData

    result = concatenate_samples([_sample(tmp_path, "s1"), _sample(tmp_path, "s2")])
    assert result.sample is not None

    fcs_path, mapping_path = export_concatenated_fcs(result.sample, result.mapping_rows, tmp_path)

    parsed = FlowData(str(fcs_path))
    assert parsed.event_count == 4
    assert parsed.channels[3]["pnn"] == "AFW_SAMPLE_INDEX"
    assert mapping_path.read_text(encoding="utf-8").startswith("sample_index,sample_id,filename,event_count")
