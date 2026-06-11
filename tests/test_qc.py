import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.qc import QCThresholds, run_sample_qc
from app.models.sample import SampleRecord


def _sample(frame: pd.DataFrame, sample_id: str = "s1") -> SampleRecord:
    record = SampleRecord(sample_id, f"{sample_id}.csv", path="unused.csv", file_type="csv", events=frame)
    record.channels = summarize_channels(frame)
    return record


def test_low_event_count_qc():
    sample = _sample(pd.DataFrame({"FSC-A": [1] * 900, "SSC-A": [2] * 900}))

    flags = run_sample_qc(sample)

    assert any(flag.code == "LOW_EVENTS_SEVERE" for flag in flags)


def test_missing_fsc_ssc_qc():
    sample = _sample(pd.DataFrame({"FITC-A": [1, 2, 3, 4, 5] * 300}))

    flags = run_sample_qc(sample)

    assert any(flag.code == "MISSING_FSC_SSC" for flag in flags)


def test_exported_fs_ss_aliases_do_not_trigger_missing_scatter_qc():
    sample = _sample(pd.DataFrame({"FS Lin": [1, 2, 3, 4, 5] * 300, "SS Lin": [2, 3, 4, 5, 6] * 300}))

    flags = run_sample_qc(sample)

    assert not any(flag.code == "MISSING_FSC_SSC" for flag in flags)


def test_saturation_qc():
    frame = pd.DataFrame({"FSC-A": list(range(1000)), "SSC-A": list(range(1000)), "FITC-A": [0] * 980 + [100] * 20})
    sample = _sample(frame)

    flags = run_sample_qc(sample, QCThresholds(low_event_warning=10, clipping_percent_warning=1.0))

    assert any(flag.code == "POSSIBLE_HIGH_CLIPPING" and flag.channel == "FITC-A" for flag in flags)
