from app.core.export_tables import export_rows_csv


def test_export_rows_csv_writes_table(tmp_path):
    path = export_rows_csv([{"sample": "s1", "count": 10}], tmp_path / "out" / "table.csv")

    assert path.exists()
    assert path.read_text(encoding="utf-8").splitlines() == ["sample,count", "s1,10"]
