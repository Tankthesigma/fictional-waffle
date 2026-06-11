import pandas as pd

from app.core.channel_inference import best_scatter_pair, infer_channel_role, summarize_channels


def test_channel_inference_common_roles():
    assert infer_channel_role("FSC-A") == "fsc-a"
    assert infer_channel_role("SSC-H") == "ssc-h"
    assert infer_channel_role("Time") == "time"
    assert infer_channel_role("FITC-A") == "fluorescence"


def test_channel_summary_best_pair():
    frame = pd.DataFrame({"FSC-A": [1, 2, 3], "SSC-A": [2, 3, 4], "FITC-A": [5, 6, 7]})
    channels = summarize_channels(frame)

    assert best_scatter_pair(channels) == ("FSC-A", "SSC-A")
    assert [c.role for c in channels] == ["fsc-a", "ssc-a", "fluorescence"]
