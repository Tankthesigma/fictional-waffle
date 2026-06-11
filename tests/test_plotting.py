import pandas as pd
import numpy as np

from app.core.channel_inference import summarize_channels
from app.core.plotting import empty_figure, histogram_figure, scatter_figure, time_stability_figure
from app.models.channel import ChannelSummary
from app.models.gate import GateDefinition
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


def _synthetic_flow_sample(sample_id: str = "demo", n_events: int = 120_000) -> SampleRecord:
    rng = np.random.default_rng(7)
    main = rng.multivariate_normal([65_000, 33_000], [[7_000**2, 2_500**2], [2_500**2, 5_000**2]], size=int(n_events * 0.78))
    shoulder = rng.multivariate_normal([31_000, 18_000], [[5_000**2, 1_800**2], [1_800**2, 4_000**2]], size=n_events - len(main))
    scatter = np.vstack([main, shoulder])
    scatter = np.clip(scatter, 1, None)
    fluorescence = rng.lognormal(mean=7.4, sigma=0.55, size=n_events)
    time = np.linspace(0, 240, n_events)
    frame = pd.DataFrame(
        {
            "FSC-A": scatter[:, 0],
            "SSC-A": scatter[:, 1],
            "FL1-A": fluorescence,
            "Time": time,
        }
    )
    sample = SampleRecord(sample_id, f"{sample_id}.fcs", path=f"{sample_id}.fcs", file_type="fcs", events=frame)
    sample.channels = [
        ChannelSummary(1, "FSC-A", role="fsc-a", minimum=float(frame["FSC-A"].min()), maximum=float(frame["FSC-A"].max()), median=float(frame["FSC-A"].median())),
        ChannelSummary(2, "SSC-A", role="ssc-a", minimum=float(frame["SSC-A"].min()), maximum=float(frame["SSC-A"].max()), median=float(frame["SSC-A"].median())),
        ChannelSummary(3, "FL1-A", role="fluorescence", minimum=float(frame["FL1-A"].min()), maximum=float(frame["FL1-A"].max()), median=float(frame["FL1-A"].median())),
        ChannelSummary(4, "Time", role="time", minimum=float(frame["Time"].min()), maximum=float(frame["Time"].max()), median=float(frame["Time"].median())),
    ]
    return sample


def test_scatter_graph_is_webgl_downsampled_gated_and_does_not_mutate_events():
    sample = _synthetic_flow_sample()
    before = sample.events.copy(deep=True)
    gate = GateDefinition(
        gate_id="g1",
        name="Main scatter review gate",
        gate_type="rectangle",
        channels=["FSC-A", "SSC-A"],
        bounds={"x_min": 45_000, "x_max": 85_000, "y_min": 20_000, "y_max": 48_000},
    )

    fig = scatter_figure(sample, "FSC-A", "SSC-A", transform="arcsinh", cofactor=150, max_events=8_000, gates=[gate])

    assert len(fig.data) == 1
    assert fig.data[0].type == "scattergl"
    assert len(fig.data[0].x) == 8_000
    assert len(fig.data[0].y) == 8_000
    assert np.all(np.isfinite(fig.data[0].x))
    assert np.all(np.isfinite(fig.data[0].y))
    assert fig.layout.dragmode == "zoom"
    assert fig.layout.xaxis.title.text == "FSC-A (arcsinh)"
    assert fig.layout.yaxis.title.text == "SSC-A (arcsinh)"
    assert fig.layout.xaxis.range is not None
    assert fig.layout.yaxis.range is not None
    assert "demo: FSC-A vs SSC-A" in fig.layout.title.text
    assert "raw events, arcsinh display, dot plot" in fig.layout.title.text
    assert len(fig.layout.shapes) == 1
    assert fig.layout.shapes[0].type == "rect"
    assert fig.layout.annotations[0].text == "Main scatter review gate"
    pd.testing.assert_frame_equal(sample.events, before)


def test_scatter_graph_gate_overlay_respects_raw_vs_compensated_views():
    sample = _synthetic_flow_sample(n_events=5_000)
    sample.compensated_events = sample.events.assign(**{"FSC-A": sample.events["FSC-A"] * 1.01})
    gate = GateDefinition(
        gate_id="raw-gate",
        name="Raw-only gate",
        gate_type="rectangle",
        channels=["FSC-A", "SSC-A"],
        bounds={"x_min": 45_000, "x_max": 85_000, "y_min": 20_000, "y_max": 48_000},
        metadata={"event_view": "raw"},
    )

    raw_fig = scatter_figure(sample, "FSC-A", "SSC-A", gates=[gate], use_compensation=False)
    compensated_fig = scatter_figure(sample, "FSC-A", "SSC-A", gates=[gate], use_compensation=True)

    assert len(raw_fig.layout.shapes) == 1
    assert len(compensated_fig.layout.shapes) == 0
    assert "metadata compensated events" in compensated_fig.layout.title.text


def test_density_plot_mode_uses_2d_bins_and_gate_overlay():
    sample = _synthetic_flow_sample(n_events=90_000)
    gate = GateDefinition(
        gate_id="density-gate",
        name="Density review gate",
        gate_type="rectangle",
        channels=["FSC-A", "SSC-A"],
        bounds={"x_min": 45_000, "x_max": 85_000, "y_min": 20_000, "y_max": 48_000},
    )

    fig = scatter_figure(sample, "FSC-A", "SSC-A", plot_mode="density", transform="arcsinh", max_events=7_500, gates=[gate])

    assert len(fig.data) == 1
    assert fig.data[0].type == "histogram2d"
    assert fig.data[0].nbinsx == 160
    assert fig.data[0].nbinsy == 160
    assert len(fig.data[0].x) == 7_500
    assert len(fig.layout.shapes) == 1
    assert "density plot" in fig.layout.title.text
    assert fig.layout.dragmode == "zoom"


def test_contour_plot_mode_uses_density_contours():
    sample = _synthetic_flow_sample(n_events=80_000)

    fig = scatter_figure(sample, "FSC-A", "SSC-A", plot_mode="contour", transform="safe_log10", max_events=6_000)

    assert len(fig.data) == 1
    assert fig.data[0].type == "histogram2dcontour"
    assert fig.data[0].ncontours == 18
    assert len(fig.data[0].x) == 6_000
    assert "contour plot" in fig.layout.title.text
    assert fig.layout.xaxis.title.text == "FSC-A (safe_log10)"


def test_log_transform_warns_when_values_are_clamped():
    sample = _synthetic_flow_sample(n_events=2_000)
    sample.events.loc[:500, "FL1-A"] = 0

    fig = histogram_figure([sample], "FL1-A", transform="safe_log10", max_events=1_000)

    assert any("clamped at the log10 floor" in annotation.text for annotation in fig.layout.annotations)


def test_compensated_log_display_switches_to_arcsinh_with_warning():
    sample = _synthetic_flow_sample(n_events=2_000)
    sample.compensated_events = sample.events.assign(**{"FL1-A": sample.events["FL1-A"] - sample.events["FL1-A"].median()})

    fig = histogram_figure([sample], "FL1-A", transform="safe_log10", use_compensation=True, max_events=1_000)

    assert "arcsinh display" in fig.layout.title.text
    assert fig.layout.xaxis.title.text == "FL1-A (arcsinh)"
    assert any("switched to arcsinh" in annotation.text for annotation in fig.layout.annotations)


def test_unknown_plot_mode_falls_back_to_dot_plot():
    sample = _synthetic_flow_sample(n_events=10_000)

    fig = scatter_figure(sample, "FSC-A", "SSC-A", plot_mode="weird")

    assert fig.data[0].type == "scattergl"
    assert "dot plot" in fig.layout.title.text


def test_histogram_overlay_uses_density_traces_for_multiple_samples():
    control = _synthetic_flow_sample("control", n_events=75_000)
    treated = _synthetic_flow_sample("treated", n_events=75_000)
    treated.events["FL1-A"] = treated.events["FL1-A"] * 1.8

    fig = histogram_figure([control, treated], "FL1-A", transform="safe_log10", max_events=9_000)

    assert len(fig.data) == 2
    assert {trace.name for trace in fig.data} == {"control", "treated"}
    assert all(trace.type == "histogram" for trace in fig.data)
    assert all(trace.histnorm == "probability density" for trace in fig.data)
    assert all(len(trace.x) == 9_000 for trace in fig.data)
    assert all(np.all(np.isfinite(trace.x)) for trace in fig.data)
    assert fig.layout.barmode == "overlay"
    assert fig.layout.xaxis.title.text == "FL1-A (safe_log10)"
    assert fig.layout.xaxis.range is not None
    assert "raw events, safe_log10 display" in fig.layout.title.text


def test_plot_titles_use_panel_marker_labels_when_present():
    sample = _synthetic_flow_sample(n_events=2_000)
    sample.channels[2].marker = "CD3"
    sample.channels[2].fluorochrome = "FITC"

    fig = histogram_figure([sample], "FL1-A", transform="arcsinh", max_events=1_000)

    assert fig.layout.xaxis.title.text == "CD3 FITC (FL1-A) (arcsinh)"
    assert "CD3 FITC (FL1-A) histogram overlay" in fig.layout.title.text


def test_plotting_empty_and_missing_channel_paths_are_friendly():
    missing = scatter_figure(_sample(), "FSC-A", "NOPE")
    empty = empty_figure("Nothing to see yet")

    assert missing.layout.annotations[0].text == "Selected channels are not available for this sample."
    assert empty.layout.annotations[0].text == "Nothing to see yet"


def test_time_stability_graph_uses_detected_time_channel():
    sample = _synthetic_flow_sample(n_events=10_000)

    fig = time_stability_figure(sample)

    assert len(fig.data) == 1
    assert fig.data[0].type == "histogram"
    assert fig.layout.title.text == "demo: event rate over Time"
