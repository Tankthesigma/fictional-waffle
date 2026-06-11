import pytest

from app.core.csv_loader import parse_manifest
from app.core.grouping import grouping_readiness_rows, grouping_readiness_summary, manifest_template_columns, manifest_template_rows
from app.models.sample import SampleRecord


def test_manifest_parsing(tmp_path):
    path = tmp_path / "manifest.csv"
    path.write_text("sample_id,file_name,condition,replicate,control_type,notes\ns1,a.fcs,control,1,untreated,ok\n", encoding="utf-8")

    manifest = parse_manifest(path)

    assert manifest["a.fcs"]["sample_id"] == "s1"
    assert manifest["a.fcs"]["condition"] == "control"


def test_manifest_duplicate_file_names_are_rejected(tmp_path):
    path = tmp_path / "manifest.csv"
    path.write_text(
        "sample_id,file_name,condition,replicate,control_type,notes\n"
        "s1,a.fcs,control,1,untreated,ok\n"
        "s2,a.fcs,treated,2,treated,nope\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate file_name"):
        parse_manifest(path)


def test_grouping_readiness_flags_missing_conditions(tmp_path):
    control = SampleRecord("c1", "c1.fcs", path=tmp_path / "c1.fcs", file_type="fcs", events=None)  # type: ignore[arg-type]
    treated = SampleRecord("t1", "t1.fcs", path=tmp_path / "t1.fcs", file_type="fcs", events=None)  # type: ignore[arg-type]
    unlabeled = SampleRecord("u1", "u1.fcs", path=tmp_path / "u1.fcs", file_type="fcs", events=None)  # type: ignore[arg-type]
    control.condition = "control"
    control.replicate = "1"
    treated.condition = "treated"
    treated.control_type = "treated"

    summary = grouping_readiness_summary([control, treated, unlabeled])
    rows = grouping_readiness_rows([control, treated, unlabeled])

    assert summary["sample_count"] == 3
    assert summary["group_count"] == 2
    assert summary["unlabeled_samples"] == 1
    assert summary["control_like"] == 1
    assert summary["treated_like"] == 1
    assert rows[1]["status"] == "needs replicate"
    assert rows[2]["status"] == "needs condition"


def test_manifest_template_rows_follow_loaded_samples(tmp_path):
    sample = SampleRecord("s1", "s1.fcs", path=tmp_path / "s1.fcs", file_type="fcs", events=None)  # type: ignore[arg-type]
    sample.condition = "control"
    sample.replicate = "1"

    rows = manifest_template_rows([sample])

    assert manifest_template_columns() == ["sample_id", "file_name", "condition", "replicate", "control_type", "notes"]
    assert rows == [
        {
            "sample_id": "s1",
            "file_name": "s1.fcs",
            "condition": "control",
            "replicate": "1",
            "control_type": "",
            "notes": "",
        }
    ]


def test_manifest_template_rows_have_generic_example_without_samples():
    rows = manifest_template_rows([])

    assert rows[0]["condition"] == "control"
    assert rows[1]["condition"] == "treated"
