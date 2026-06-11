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


def test_csv_with_missing_numeric_values_warns(tmp_path):
    path = tmp_path / "nan.csv"
    path.write_text(
        "FSC-A,SSC-A,FL1-A\n"
        "1,2,10\n"
        "2,,20\n"
        "3,6,\n"
        "4,8,40\n"
        "5,10,50\n"
        "6,12,60\n"
        "7,14,70\n"
        "8,16,80\n"
        "9,18,90\n"
        "10,20,100\n",
        encoding="utf-8",
    )

    result = load_csv_file(path)

    assert result.sample is not None
    assert any("missing numeric value" in warning for warning in result.warnings)
