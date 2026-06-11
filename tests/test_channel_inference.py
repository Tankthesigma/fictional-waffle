import pandas as pd

from app.core.channel_inference import best_scatter_pair, infer_channel_role, summarize_channels


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


def test_channel_summary_best_pair():
    frame = pd.DataFrame({"FSC-A": [1, 2, 3], "SSC-A": [2, 3, 4], "FITC-A": [5, 6, 7]})
    channels = summarize_channels(frame)

    assert best_scatter_pair(channels) == ("FSC-A", "SSC-A")
    assert [c.role for c in channels] == ["fsc-a", "ssc-a", "fluorescence"]


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
