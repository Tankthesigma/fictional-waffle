from app.core.paths import EXPORT_ROOT, GATES_PATH, PROJECT_ROOT, TEMPLATE_PATH, UPLOAD_ROOT


def test_runtime_paths_are_project_rooted():
    assert PROJECT_ROOT.is_absolute()
    assert UPLOAD_ROOT == PROJECT_ROOT / "app_data" / "uploads"
    assert EXPORT_ROOT == PROJECT_ROOT / "exports"
    assert GATES_PATH == EXPORT_ROOT / "gates.json"
    assert TEMPLATE_PATH == EXPORT_ROOT / "ask-flow-analysis-template.json"
