import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.plotting import histogram_figure, scatter_figure
from app.models.sample import SampleRecord


def _sample() -> SampleRecord:
    frame = pd.DataFrame({"FSC-A": [1, 2, 3], "SSC-A": [1, 4, 9], "FL1-A": [10, 20, 30]})
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)
    return sample


def test_scatter_handles_bad_transform_without_throwing():
    fig = scatter_figure(_sample(), "FSC-A", "SSC-A", transform="definitely_bad")

    assert fig.layout.annotations[0].text.startswith("definitely_bad transform could not be displayed")


def test_histogram_handles_bad_transform_without_throwing():
    fig = histogram_figure([_sample()], "FL1-A", transform="definitely_bad")

    assert fig.layout.annotations[0].text.startswith("definitely_bad transform could not be displayed")
