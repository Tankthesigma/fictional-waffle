import pandas as pd

from app.core.grouping import grouping_readiness_summary
from app.models.sample import SampleRecord


def test_grouping_does_not_count_untreated_as_treated(tmp_path):
    samples = [
        _sample("c1", "control", "untreated", tmp_path),
        _sample("c2", "control", "vehicle", tmp_path),
        _sample("t1", "treated", "treated", tmp_path),
        _sample("t2", "stimulated", "drug-treated", tmp_path),
    ]

    summary = grouping_readiness_summary(samples)

    assert summary["control_like"] == 2
    assert summary["treated_like"] == 2


def _sample(sample_id: str, condition: str, control_type: str, tmp_path) -> SampleRecord:
    sample = SampleRecord(sample_id, f"{sample_id}.csv", path=tmp_path / f"{sample_id}.csv", file_type="csv", events=pd.DataFrame({"FL1-A": [1]}))
    sample.condition = condition
    sample.control_type = control_type
    return sample
