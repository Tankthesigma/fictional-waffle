from app.core.csv_loader import parse_manifest
import pytest


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
