import pandas as pd

from app.core.downsample import downsample_events


def test_downsampling_preserves_shape_expectations():
    frame = pd.DataFrame({"a": range(100), "b": range(100, 200)})

    sampled = downsample_events(frame, max_events=25, random_state=1)

    assert sampled.shape == (25, 2)
    assert list(sampled.columns) == ["a", "b"]


def test_downsampling_returns_copy_when_small():
    frame = pd.DataFrame({"a": [1, 2]})

    sampled = downsample_events(frame, max_events=10)

    assert sampled.equals(frame)
    assert sampled is not frame
