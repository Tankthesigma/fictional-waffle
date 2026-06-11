from app.core.csv_loader import load_csv_file


def test_single_channel_event_csv_is_not_labeled_summary(tmp_path):
    path = tmp_path / "single.csv"
    path.write_text("FITC-A\n" + "\n".join(str(value) for value in range(50)), encoding="utf-8")

    result = load_csv_file(path)

    assert result.sample is not None
    assert result.sample.events.shape == (50, 1)
    assert result.sample.limitations == ["CSV has one numeric channel; scatter plots and FSC/SSC QC are limited."]
    assert not any("summary" in warning.lower() for warning in result.warnings)


def test_header_only_csv_returns_friendly_error(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("FSC-A,SSC-A\n", encoding="utf-8")

    result = load_csv_file(path)

    assert result.sample is None
    assert "contains no event rows" in result.errors[0]


def test_nonnumeric_csv_returns_friendly_error(tmp_path):
    path = tmp_path / "labels.csv"
    path.write_text("name,condition\na,control\nb,treated\n", encoding="utf-8")

    result = load_csv_file(path)

    assert result.sample is None
    assert "contains no numeric event columns" in result.errors[0]
