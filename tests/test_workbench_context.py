import pandas as pd

from app.core.channel_inference import summarize_channels
from app.models.gate import GateDefinition
from app.models.sample import SampleRecord
from app.ui.callbacks_plots import _visible_gate_count
from app.ui.callbacks_sample import _channel_badges


def test_channel_badges_surface_panel_labels_for_lab_review():
    frame = pd.DataFrame({"FSC-A": [1, 2], "SSC-A": [3, 4], "FL1-A": [10, 20], "Time": [0, 1]})
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)
    sample.channels[2].marker = "CD3"
    sample.channels[2].antibody = "UCHT1"
    sample.channels[2].fluorochrome = "FITC"

    badges = _channel_badges(sample)
    text = " ".join(str(badge.to_plotly_json()) for badge in badges)

    assert "CD3 FITC (FL1-A)" in text
    assert "UCHT1" in text
    assert "fsc-a" in text
    assert "ssc-a" in text


def test_visible_gate_count_matches_only_compatible_plot_view():
    raw_gate = GateDefinition(
        gate_id="raw",
        name="Raw gate",
        gate_type="rectangle",
        channels=["FSC-A", "SSC-A"],
        bounds={"x_min": 1, "x_max": 2, "y_min": 3, "y_max": 4},
        metadata={"event_view": "raw"},
    )
    compensated_gate = GateDefinition(
        gate_id="comp",
        name="Comp gate",
        gate_type="rectangle",
        channels=["FSC-A", "SSC-A"],
        bounds={"x_min": 1, "x_max": 2, "y_min": 3, "y_max": 4},
        metadata={"event_view": "metadata_compensated"},
    )
    disabled_gate = GateDefinition(
        gate_id="disabled",
        name="Disabled gate",
        gate_type="rectangle",
        channels=["FSC-A", "SSC-A"],
        bounds={"x_min": 1, "x_max": 2, "y_min": 3, "y_max": 4},
        enabled=False,
    )

    gates = [raw_gate, compensated_gate, disabled_gate]

    assert _visible_gate_count(gates, "FSC-A", "SSC-A", use_compensation=False) == 1
    assert _visible_gate_count(gates, "FSC-A", "SSC-A", use_compensation=True) == 1
    assert _visible_gate_count(gates, "FL1-A", "SSC-A", use_compensation=False) == 0
