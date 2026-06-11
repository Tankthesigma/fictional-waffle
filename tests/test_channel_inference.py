import pandas as pd

from app.core.channel_inference import best_scatter_pair, infer_channel_role, summarize_channels
from app.core.channel_overrides import channel_role, update_channel_role
from app.models.sample import SampleRecord


def test_channel_inference_common_roles():
    assert infer_channel_role("FSC-A") == "fsc-a"
    assert infer_channel_role("SSC-H") == "ssc-h"
    assert infer_channel_role("Time") == "time"
    assert infer_channel_role("FITC-A") == "fluorescence"
    assert infer_channel_role("PE-A") == "fluorescence"
    assert infer_channel_role("BV421-A") == "fluorescence"
    assert infer_channel_role("Speed") == "unknown"
    assert infer_channel_role("Draft") == "unknown"
    assert infer_channel_role("Temperature") == "unknown"
    assert infer_channel_role("FS Lin", "FS") == "fsc"
    assert infer_channel_role("SS Lin", "SS") == "ssc"
    assert infer_channel_role("SS Log", "SS") == "ssc"
    assert infer_channel_role("FSA status") == "unknown"


def test_channel_summary_best_pair():
    frame = pd.DataFrame({"FSC-A": [1, 2, 3], "SSC-A": [2, 3, 4], "FITC-A": [5, 6, 7]})
    channels = summarize_channels(frame)

    assert best_scatter_pair(channels) == ("FSC-A", "SSC-A")
    assert [c.role for c in channels] == ["fsc-a", "ssc-a", "fluorescence"]


def test_channel_summary_best_pair_from_exported_fs_ss_aliases():
    frame = pd.DataFrame({"FS Lin": [1, 2, 3], "SS Lin": [2, 3, 4], "FL 1 Log": [5, 6, 7]})
    metadata = {"$P1S": "FS", "$P2S": "SS", "$P3S": "FITC"}
    channels = summarize_channels(frame, metadata)

    assert best_scatter_pair(channels) == ("FS Lin", "SS Lin")
    assert [c.role for c in channels] == ["fsc", "ssc", "fluorescence"]


def test_channel_metadata_prefixes_do_not_bleed_into_double_digit_channels():
    frame = pd.DataFrame({f"CH{i}": [i, i + 1, i + 2] for i in range(1, 13)})
    metadata = {
        "$P1N": "CH1",
        "$P1S": "Marker 1",
        "$P1R": "1024",
        "$P10N": "CH10",
        "$P10S": "Marker 10",
        "$P10R": "4096",
        "$P12N": "CH12",
    }

    channels = summarize_channels(frame, metadata)

    assert channels[0].display_label == "Marker 1"
    assert channels[0].range_value == 1024
    assert sorted(channels[0].metadata) == ["$P1N", "$P1R", "$P1S"]
    assert "$P10N" not in channels[0].metadata
    assert channels[9].display_label == "Marker 10"


def test_channel_role_override_updates_role_and_metadata(tmp_path):
    frame = pd.DataFrame({"A": [1, 2, 3], "B": [2, 3, 4]})
    sample = SampleRecord("s1", "s1.csv", path=tmp_path / "s1.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)

    status = update_channel_role(sample, "A", "fsc-a")

    assert status == "A: unknown -> fsc-a"
    assert sample.channels[0].role == "fsc-a"
    assert sample.channels[0].metadata["user_role_override"] == "fsc-a"


def test_channel_role_override_rejects_bad_inputs(tmp_path):
    sample = SampleRecord("s1", "s1.csv", path=tmp_path / "s1.csv", file_type="csv", events=pd.DataFrame({"A": [1]}))
    sample.channels = summarize_channels(sample.events)

    try:
        update_channel_role(sample, "A", "hardware-control")
    except ValueError as exc:
        assert "unsupported channel role" in str(exc)
    else:
        raise AssertionError("unsupported role was accepted")


def test_channel_role_lookup_returns_current_role_for_safe_ui_defaults(tmp_path):
    frame = pd.DataFrame({"FSC-A": [1, 2, 3], "FL1-A": [2, 3, 4]})
    sample = SampleRecord("s1", "s1.csv", path=tmp_path / "s1.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)

    assert channel_role(sample, "FSC-A") == "fsc-a"
    assert channel_role(sample, "FL1-A") == "fluorescence"
    assert channel_role(sample, "missing") is None
