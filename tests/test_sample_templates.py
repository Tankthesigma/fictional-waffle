from pathlib import Path

import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.csv_loader import parse_manifest
from app.core.panel_setup import apply_panel_setup, parse_panel_setup
from app.models.sample import SampleRecord


ROOT = Path(__file__).resolve().parents[1]


def test_demo_manifest_template_parses():
    manifest = parse_manifest(ROOT / "sample_data" / "demo_manifest.csv")

    row = manifest["Beckman Coulter - Cyan.fcs"]
    assert row["sample_id"] == "demo_control"
    assert row["condition"] == "control"


def test_demo_panel_template_applies_to_public_demo_channel_names():
    frame = pd.DataFrame(
        {
            "FS Lin": [1, 2, 3],
            "SS Lin": [4, 5, 6],
            "FL 1 Log": [10, 20, 30],
            "FL 2 Area": [40, 50, 60],
        }
    )
    sample = SampleRecord("demo", "Beckman Coulter - Cyan.fcs", path="unused.fcs", file_type="fcs", events=frame)
    sample.channels = summarize_channels(frame)

    warnings = apply_panel_setup([sample], parse_panel_setup(ROOT / "sample_data" / "demo_panel_setup.csv"))

    assert warnings == []
    by_name = {channel.raw_name: channel for channel in sample.channels}
    assert by_name["FS Lin"].role == "fsc"
    assert by_name["SS Lin"].role == "ssc"
    assert by_name["FL 1 Log"].marker == "Example FITC marker"
    assert by_name["FL 1 Log"].fluorochrome == "FITC"
    assert by_name["FL 1 Log"].label == "Example FITC marker FITC (FL 1 Log)"
