import json

from app.main import create_app


def test_app_registers_expected_callbacks():
    dash_app = create_app()

    assert dash_app.title == "Ask Flow Workbench"
    assert len(dash_app.callback_map) >= 12
    assert "scatter-graph.figure" in dash_app.callback_map
    assert "compensation-status.children" in dash_app.callback_map
    assert any("median-table.columns" in key for key in dash_app.callback_map)
    assert any("gate-stats-table.columns" in key for key in dash_app.callback_map)


def test_layout_does_not_offer_unwired_draw_gate_tools():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "drawrect" not in layout_json
    assert "eraseshape" not in layout_json


def test_repeated_shell_disclaimer_is_not_rendered():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "Post-acquisition analysis only. This app does not control cytometer hardware and does not replace expert review." not in layout_json


def test_low_key_ui_safety_boundary_is_rendered():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "Exploratory only; does not control cytometer hardware and does not replace expert review." in layout_json
