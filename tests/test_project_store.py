import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.gating import rectangle_gate
from app.core.project_store import build_project_state, gates_from_project, load_project, save_project
from app.models.project_schema import ProjectState
from app.models.sample import SampleRecord


def test_project_save_load(tmp_path):
    project = ProjectState(project_title="Demo", sample_metadata=[{"sample_id": "s1"}], gate_definitions=[{"gate_id": "g1"}])
    path = tmp_path / "project.json"

    save_project(project, path)
    loaded = load_project(path)

    assert loaded.project_title == "Demo"
    assert loaded.sample_metadata == [{"sample_id": "s1"}]
    assert loaded.gate_definitions == [{"gate_id": "g1"}]


def test_build_project_state_excludes_raw_event_matrix(tmp_path):
    frame = pd.DataFrame({"FSC-A": [1, 2], "SSC-A": [3, 4], "FL1-A": [10, 20]})
    sample = SampleRecord("s1", "s1.csv", path=tmp_path / "s1.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 3, 0, 5)

    project = build_project_state(
        [sample],
        [gate],
        [],
        transform_settings={"transform": "arcsinh"},
        comparison_settings={"control_group": "untreated"},
    )

    payload = project.to_dict()
    text = str(payload)
    assert payload["sample_metadata"][0]["sample_id"] == "s1"
    assert payload["sample_metadata"][0]["event_count"] == 2
    assert payload["gate_definitions"][0]["gate_id"] == "g1"
    assert payload["transform_settings"]["transform"] == "arcsinh"
    assert "events" not in payload["sample_metadata"][0]
    assert "[1, 2]" not in text
    assert gates_from_project(project)[0].to_dict() == gate.to_dict()
