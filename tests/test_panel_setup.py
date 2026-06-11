import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.panel_setup import apply_panel_setup, parse_panel_setup
from app.models.sample import SampleRecord


def _sample() -> SampleRecord:
    frame = pd.DataFrame({"FSC-A": [1, 2], "FL1-A": [10, 20]})
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)
    return sample


def test_parse_panel_setup_and_apply_marker_labels(tmp_path):
    path = tmp_path / "panel.csv"
    path.write_text(
        "channel,display_label,marker,antibody,fluorochrome,role\n"
        "FL1-A,FITC detector,CD3,UCHT1,FITC,fluorescence\n",
        encoding="utf-8",
    )
    sample = _sample()

    panel = parse_panel_setup(path)
    warnings = apply_panel_setup([sample], panel)

    fl1 = sample.channels[1]
    assert warnings == []
    assert fl1.display_label == "FITC detector"
    assert fl1.marker == "CD3"
    assert fl1.antibody == "UCHT1"
    assert fl1.fluorochrome == "FITC"
    assert fl1.role == "fluorescence"
    assert fl1.label == "CD3 FITC (FL1-A)"
    assert fl1.to_dict()["marker"] == "CD3"


def test_panel_setup_rejects_duplicate_channel_keys(tmp_path):
    path = tmp_path / "panel.csv"
    path.write_text("channel,marker\nFL1-A,CD3\nFL1-A,CD4\n", encoding="utf-8")

    try:
        parse_panel_setup(path)
    except ValueError as exc:
        assert "duplicate channel key" in str(exc)
    else:
        raise AssertionError("duplicate panel keys were accepted")


def test_panel_setup_warns_when_no_channels_match(tmp_path):
    path = tmp_path / "panel.csv"
    path.write_text("channel,marker\nPE-A,CD19\n", encoding="utf-8")
    sample = _sample()

    warnings = apply_panel_setup([sample], parse_panel_setup(path))

    assert warnings == ["s1.csv: panel setup did not match any channels."]
