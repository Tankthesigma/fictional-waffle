import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.plot_presets import plot_preset_rows, recommended_plot_presets, resolve_plot_preset
from app.models.sample import SampleRecord


def _sample(columns: list[str]) -> SampleRecord:
    frame = pd.DataFrame({column: [1, 2, 3, 4, 5] for column in columns})
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)
    return sample


def test_recommended_plot_presets_cover_scatter_singlet_marker_and_time_views():
    sample = _sample(["FSC-A", "FSC-H", "SSC-A", "FL1-A", "Time"])
    sample.channels[3].marker = "CD3"
    sample.channels[3].fluorochrome = "FITC"

    presets = recommended_plot_presets(sample)
    ids = [preset.preset_id for preset in presets]

    assert ids == ["scatter-cleanup", "singlet-check", "marker-histogram", "time-review"]
    assert presets[0].x_channel == "FSC-A"
    assert presets[0].y_channel == "SSC-A"
    assert presets[0].plot_mode == "density"
    assert presets[1].x_channel == "FSC-A"
    assert presets[1].y_channel == "FSC-H"
    assert presets[2].label == "CD3 FITC Histogram"
    assert presets[2].hist_channel == "FL1-A"
    assert presets[3].x_channel == "Time"


def test_resolve_plot_preset_defaults_to_first_recommendation():
    sample = _sample(["FSC-A", "SSC-A", "FL1-A"])

    preset = resolve_plot_preset(sample, None)

    assert preset is not None
    assert preset.preset_id == "scatter-cleanup"


def test_plot_preset_rows_explain_why_each_view_exists():
    sample = _sample(["FSC-A", "SSC-A", "FL1-A"])

    rows = plot_preset_rows(sample)

    assert rows[0]["preset"] == "Scatter Cleanup"
    assert rows[0]["scatter"] == "FSC-A x SSC-A"
    assert "main-population review" in rows[0]["why"]


def test_plot_presets_fallback_when_roles_are_unknown():
    sample = _sample(["A", "B", "C"])

    presets = recommended_plot_presets(sample)

    assert len(presets) == 1
    assert presets[0].preset_id == "first-two-channels"
    assert presets[0].x_channel == "A"
    assert presets[0].y_channel == "B"
