import json

import pandas as pd

from app.core.analysis_templates import (
    apply_template_channel_annotations,
    build_analysis_template,
    gates_from_template,
    load_analysis_template,
    save_analysis_template,
)
from app.core.channel_inference import summarize_channels
from app.core.gating import rectangle_gate
from app.models.sample import SampleRecord


def test_analysis_template_save_load_excludes_raw_events_and_file_refs(tmp_path):
    frame = pd.DataFrame({"FSC-A": [1, 2], "SSC-A": [3, 4], "FL1-A": [10, 20]})
    sample = SampleRecord("s1", "secret.fcs", path=tmp_path / "secret.fcs", file_type="fcs", events=frame)
    sample.channels = summarize_channels(frame)
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 3, 0, 5)

    template = build_analysis_template(
        [sample],
        [gate],
        plot_settings={"transform": "arcsinh", "x_channel": "FSC-A"},
        comparison_settings={"control_group": "control"},
    )
    path = save_analysis_template(template, tmp_path / "template.json")
    text = path.read_text(encoding="utf-8")
    loaded = load_analysis_template(path)

    assert loaded.plot_settings["transform"] == "arcsinh"
    assert loaded.comparison_settings["control_group"] == "control"
    assert loaded.gate_definitions[0]["gate_id"] == "g1"
    assert "secret.fcs" not in text
    assert str(tmp_path) not in text
    assert "[1, 2]" not in text
    assert "events" not in json.loads(text)


def test_analysis_template_restores_gates(tmp_path):
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 3, 0, 5)
    gate.metadata["event_view"] = "raw"
    template = build_analysis_template([], [gate])

    restored = gates_from_template(template)

    assert restored[0].to_dict() == gate.to_dict()


def test_analysis_template_applies_channel_annotations(tmp_path):
    saved_frame = pd.DataFrame({"FSC-A": [1, 2], "FL1-A": [10, 20]})
    saved = SampleRecord("saved", "saved.csv", path=tmp_path / "saved.csv", file_type="csv", events=saved_frame)
    saved.channels = summarize_channels(saved_frame)
    saved.channels[1].display_label = "FITC detector"
    saved.channels[1].marker = "CD3"
    saved.channels[1].antibody = "UCHT1"
    saved.channels[1].fluorochrome = "FITC"
    saved.channels[1].role = "fluorescence"
    template = build_analysis_template([saved], [])

    current = SampleRecord("current", "current.csv", path=tmp_path / "current.csv", file_type="csv", events=saved_frame)
    current.channels = summarize_channels(saved_frame)
    applied = apply_template_channel_annotations([current], template)

    assert applied == 2
    assert current.channels[1].display_label == "FITC detector"
    assert current.channels[1].marker == "CD3"
    assert current.channels[1].antibody == "UCHT1"
    assert current.channels[1].fluorochrome == "FITC"
    assert current.channels[1].role == "fluorescence"


def test_analysis_template_rejects_non_list_gate_definitions(tmp_path):
    path = tmp_path / "bad-template.json"
    path.write_text('{"gate_definitions": "notalist"}', encoding="utf-8")

    try:
        load_analysis_template(path)
    except ValueError as exc:
        assert "gate_definitions must be a list" in str(exc)
    else:
        raise AssertionError("load_analysis_template accepted invalid gate_definitions")
