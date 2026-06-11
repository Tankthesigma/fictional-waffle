from app.main import create_app


def test_app_registers_expected_callbacks():
    dash_app = create_app()

    assert dash_app.title == "Ask Flow Workbench"
    assert len(dash_app.callback_map) >= 12
    assert "scatter-graph.figure" in dash_app.callback_map
    assert "compensation-status.children" in dash_app.callback_map
    assert any("median-table.columns" in key for key in dash_app.callback_map)
    assert any("gate-stats-table.columns" in key for key in dash_app.callback_map)
