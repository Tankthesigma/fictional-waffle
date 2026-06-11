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


def test_panel_setup_upload_is_rendered():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "upload-panel" in layout_json
    assert "Optional panel setup CSV" in layout_json
    assert "download-panel-template" in layout_json
    assert "Download Panel Template" in layout_json
    assert "panel-template-download" in layout_json
    assert "load-demo-data" in layout_json
    assert "Load Demo Dataset" in layout_json


def test_candidate_gate_controls_are_rendered_with_review_language():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "suggest-candidate-gates" in layout_json
    assert "add-review-current-view-gate" in layout_json
    assert "Quick Gate Current View" in layout_json
    assert "add-review-scatter-gate" in layout_json
    assert "Add Review FSC/SSC Gate" in layout_json
    assert "accept-candidate-gates" in layout_json
    assert "reject-candidate-gates" in layout_json
    assert "Candidate gates are review-needed and disabled until accepted" in layout_json


def test_gate_manager_controls_are_rendered():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "gate-stack-cards" in layout_json
    assert "manage-gate-id" in layout_json
    assert "rename-gate" in layout_json
    assert "toggle-gate" in layout_json
    assert "delete-gate" in layout_json


def test_compare_summary_container_is_rendered():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "Select control group" in layout_json
    assert "Select treated group" in layout_json
    assert "compare-summary-cards" in layout_json
    assert "compare-insights" in layout_json
    assert "comparison-delta-chart" in layout_json
    assert any("comparison-delta-chart.figure" in key for key in dash_app.callback_map)
    assert any("compare-insights.children" in key for key in dash_app.callback_map)
    assert any("control-group.options" in key for key in dash_app.callback_map)


def test_qc_review_lanes_are_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "qc-review-lanes" in layout_json
    assert any("qc-review-lanes.children" in key for key in dash_app.callback_map)


def test_report_readiness_preview_is_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "report-readiness" in layout_json
    assert "report-readiness.children" in dash_app.callback_map


def test_ask_flow_briefing_is_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "ask-flow-briefing" in layout_json
    assert "Local deterministic summaries only" in layout_json
    assert "ask-flow-briefing.children" in dash_app.callback_map


def test_workbench_analysis_cockpit_is_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "active-analysis-strip" in layout_json
    assert "analysis-guide" in layout_json
    assert "plot-context-bar" in layout_json
    assert "channel-badge-rail" in layout_json
    assert "Population workflow" in layout_json
    assert "Display stack" in layout_json
    assert "Stats use full matrix" in layout_json
    assert "Panel Setup Readiness" in layout_json
    assert "panel-readiness-summary" in layout_json
    assert "panel-readiness-table" in layout_json
    assert "Analysis preset" in layout_json
    assert "plot-preset" in layout_json
    assert "Apply Preset" in layout_json
    assert "plot-preset-table" in layout_json
    assert any("active-analysis-strip.children" in key for key in dash_app.callback_map)
    assert "analysis-guide.children" in dash_app.callback_map
    assert any("plot-context-bar.children" in key for key in dash_app.callback_map)
    assert any("panel-readiness-summary.children" in key for key in dash_app.callback_map)
    assert "panel-template-download.data" in dash_app.callback_map
    assert any("plot-preset.options" in key for key in dash_app.callback_map)
    assert any("plot-preset-status.children" in key for key in dash_app.callback_map)
