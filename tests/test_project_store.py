from app.core.project_store import load_project, save_project
from app.models.project_schema import ProjectState


def test_project_save_load(tmp_path):
    project = ProjectState(project_title="Demo", sample_metadata=[{"sample_id": "s1"}], gate_definitions=[{"gate_id": "g1"}])
    path = tmp_path / "project.json"

    save_project(project, path)
    loaded = load_project(path)

    assert loaded.project_title == "Demo"
    assert loaded.sample_metadata == [{"sample_id": "s1"}]
    assert loaded.gate_definitions == [{"gate_id": "g1"}]
