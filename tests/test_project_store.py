import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.gating import rectangle_gate
from app.core.project_store import apply_project_sample_metadata, build_project_state, gates_from_project, load_project, save_project
from app.models.gate import GateDefinition
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


def test_project_rejects_non_list_gate_definitions(tmp_path):
    path = tmp_path / "project.json"
    path.write_text('{"gate_definitions": "notalist"}', encoding="utf-8")

    try:
        load_project(path)
    except ValueError as exc:
        assert "gate_definitions must be a list" in str(exc)
    else:
        raise AssertionError("load_project accepted invalid gate_definitions")


def test_gate_definition_rejects_bad_polygon_vertices():
    payload = {
        "gate_id": "poly",
        "gate_type": "polygon",
        "channels": ["FSC-A", "SSC-A"],
        "vertices": [[0, 0, 1], [1, 1]],
    }

    try:
        GateDefinition.from_dict(payload)
    except ValueError as exc:
        assert "polygon vertices must be [x, y] pairs" in str(exc)
    else:
        raise AssertionError("bad polygon vertices were accepted")


def test_unknown_gate_type_loads_with_warning_for_forward_compatibility():
    gate = GateDefinition.from_dict({"gate_id": "future1", "gate_type": "future_gate", "channels": ["FSC-A", "SSC-A"]})

    assert gate.gate_type == "future_gate"
    assert gate.metadata["mask_warning"] == "unsupported gate type: future_gate"


def test_project_round_trip_preserves_panel_annotations_and_candidate_state(tmp_path):
    frame = pd.DataFrame({"FSC-A": [1, 2], "FL1-A": [10, 20]})
    sample = SampleRecord("s1", "s1.csv", path=tmp_path / "s1.csv", file_type="csv", events=frame)
    sample.condition = "treated"
    sample.channels = summarize_channels(frame)
    sample.channels[1].display_label = "FITC detector"
    sample.channels[1].marker = "CD3"
    sample.channels[1].antibody = "UCHT1"
    sample.channels[1].fluorochrome = "FITC"
    gate = rectangle_gate("candidate", "candidate main", "FSC-A", "FL1-A", 0, 3, 0, 30)
    gate.enabled = False
    gate.candidate = True
    gate.user_defined = False
    gate.review_status = "review_needed"
    gate.metadata["candidate_reason"] = "review before use"

    project = build_project_state([sample], [gate], [])
    path = save_project(project, tmp_path / "project.json")
    loaded = load_project(path)
    restored_gate = gates_from_project(loaded)[0]

    assert loaded.sample_metadata[0]["channels"][1]["marker"] == "CD3"
    assert restored_gate.candidate is True
    assert restored_gate.enabled is False
    assert restored_gate.review_status == "review_needed"
    assert restored_gate.metadata["candidate_reason"] == "review before use"


def test_apply_project_sample_metadata_restores_annotations_to_loaded_samples(tmp_path):
    saved_frame = pd.DataFrame({"FSC-A": [1, 2], "FL1-A": [10, 20]})
    saved = SampleRecord("s1", "s1.csv", path=tmp_path / "s1.csv", file_type="csv", events=saved_frame)
    saved.condition = "control"
    saved.channels = summarize_channels(saved_frame)
    saved.channels[1].marker = "CD19"
    saved.channels[1].fluorochrome = "PE"
    project = build_project_state([saved], [], [])

    current = SampleRecord("s1", "s1.csv", path=tmp_path / "s1.csv", file_type="csv", events=saved_frame)
    current.channels = summarize_channels(saved_frame)

    applied = apply_project_sample_metadata([current], project)

    assert applied == 2
    assert current.condition == "control"
    assert current.channels[1].marker == "CD19"
    assert current.channels[1].fluorochrome == "PE"
    assert current.channels[1].label == "CD19 PE (FL1-A)"
