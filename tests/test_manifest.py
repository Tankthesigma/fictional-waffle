from app.core.csv_loader import parse_manifest


def test_manifest_parsing(tmp_path):
    path = tmp_path / "manifest.csv"
    path.write_text("sample_id,file_name,condition,replicate,control_type,notes\ns1,a.fcs,control,1,untreated,ok\n", encoding="utf-8")

    manifest = parse_manifest(path)

    assert manifest["a.fcs"]["sample_id"] == "s1"
    assert manifest["a.fcs"]["condition"] == "control"
