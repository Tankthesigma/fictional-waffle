import json
from pathlib import Path

from app.main import create_app


def test_app_registers_expected_callbacks():
    dash_app = create_app()

    assert dash_app.title == "Ask Flow Workbench"
    assert len(dash_app.callback_map) >= 12
    assert "scatter-graph.figure" in dash_app.callback_map
    assert "compensation-status.children" in dash_app.callback_map
    assert any("median-table.columns" in key for key in dash_app.callback_map)
    assert any("gate-stats-table.columns" in key for key in dash_app.callback_map)


def test_layout_offers_wired_draw_gate_tools():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "last-drawn-gate-store" in layout_json
    assert "displaylogo" in layout_json
    assert "False" in layout_json
    assert "drawrect" in layout_json
    assert "drawclosedpath" in layout_json
    assert "eraseshape" in layout_json
    assert any(
        any(item.get("id") == "scatter-graph" and item.get("property") == "relayoutData" for item in callback.get("inputs", []))
        for callback in dash_app.callback_map.values()
    )


def test_repeated_shell_disclaimer_is_not_rendered():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "Post-acquisition analysis only. This app does not control cytometer hardware and does not replace expert review." not in layout_json


def test_low_key_ui_safety_boundary_is_rendered():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "Post-acquisition research review | no cytometer control | expert review required." in layout_json


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
    assert "create-singlet-gate" in layout_json
    assert "Create Singlet Gate" in layout_json
    assert "ai-auto-gate-clusters" in layout_json
    assert "Cluster-Guided Gate Review" in layout_json
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
    assert "export-gated-fcs" in layout_json
    assert "Export Selected Gate as FCS" in layout_json
    assert "export-gated-csv" in layout_json
    assert "Export Selected Gate as CSV" in layout_json
    assert "add-boolean-gate" in layout_json
    assert "boolean-gate-a" in layout_json
    assert "boolean-gate-b" in layout_json
    assert any("boolean-gate-a.options" in key for key in dash_app.callback_map)


def test_analysis_template_controls_are_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "save-analysis-template" in layout_json
    assert "Save Analysis Template" in layout_json
    assert "load-analysis-template" in layout_json
    assert "Load Analysis Template" in layout_json
    assert "template-status" in layout_json
    assert any("template-status.children" in key for key in dash_app.callback_map)


def test_compare_summary_container_is_rendered():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "Select control group" in layout_json
    assert "Select treated group" in layout_json
    assert "grouping-readiness-summary" in layout_json
    assert "grouping-readiness-table" in layout_json
    assert "Download Manifest Template" in layout_json
    assert "manifest-template-download" in layout_json
    assert "compare-summary-cards" in layout_json
    assert "compare-insights" in layout_json
    assert "comparison-delta-chart" in layout_json
    assert "batch-apply-gates" in layout_json
    assert "population-frequency-table" in layout_json
    assert "export-population-frequency-csv" in layout_json
    assert "concatenate-samples" in layout_json
    assert "Concatenate Loaded Samples" in layout_json
    assert "export-concatenated-fcs" in layout_json
    assert "Export Concatenated FCS" in layout_json
    assert any("grouping-readiness-summary.children" in key for key in dash_app.callback_map)
    assert "manifest-template-download.data" in dash_app.callback_map
    assert any("comparison-delta-chart.figure" in key for key in dash_app.callback_map)
    assert any("compare-insights.children" in key for key in dash_app.callback_map)
    assert any("control-group.options" in key for key in dash_app.callback_map)
    assert any("population-frequency-table.columns" in key for key in dash_app.callback_map)


def test_qc_review_lanes_are_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "qc-review-lanes" in layout_json
    assert any("qc-review-lanes.children" in key for key in dash_app.callback_map)


def test_report_readiness_preview_is_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "report-readiness" in layout_json
    assert "report-outline-preview" in layout_json
    assert any("report-readiness.children" in key for key in dash_app.callback_map)
    assert any("report-outline-preview.children" in key for key in dash_app.callback_map)


def test_ask_flow_briefing_is_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "ask-flow-briefing" in layout_json
    assert "Analysis review console for plots, QC, gates, high-dimensional clusters" in layout_json
    assert "ask-flow-plan" in layout_json
    assert "Review Plan" in layout_json
    assert "High-Dimensional Review" in layout_json
    assert "high-dimensional-graph" in layout_json
    assert "high-dimensional-cluster-table" in layout_json
    assert "ask-flow-agent-status" in layout_json
    assert "Workbench actions:" in layout_json
    assert "toast-container" in layout_json
    assert "toast-store" in layout_json
    assert "toast-timer" in layout_json
    assert "ask-flow-loading" in layout_json
    assert "ask-flow-answer-loading" in layout_json
    assert any("toast-store.data" in key for key in dash_app.callback_map)
    assert any("toast-container.children" in key for key in dash_app.callback_map)
    assert any("ask-flow-briefing.children" in key for key in dash_app.callback_map)
    assert any("ask-flow-plan.children" in key for key in dash_app.callback_map)
    assert any("ask-flow-agent-status.children" in key for key in dash_app.callback_map)
    assert any("high-dimensional-graph.figure" in key for key in dash_app.callback_map)


def test_workbench_tabs_have_compact_horizontal_css():
    css = Path("app/assets/style.css").read_text(encoding="utf-8")

    assert ".center-panel .tab-container" in css
    assert "flex-direction: row !important" in css
    assert ".center-panel .tab--selected" in css
    assert "width: auto !important" in css


def test_workbench_analysis_cockpit_is_rendered_and_wired():
    dash_app = create_app()
    layout_json = json.dumps(dash_app.layout.to_plotly_json(), default=str)

    assert "analysis-revision-store" in layout_json
    assert "active-analysis-strip" in layout_json
    assert "analysis-guide" in layout_json
    assert "plot-context-bar" in layout_json
    assert "channel-badge-rail" in layout_json
    assert "Population workflow" in layout_json
    assert "Data view" in layout_json
    assert "Stats use full matrix" in layout_json
    assert "Panel Setup Readiness" in layout_json
    assert "panel-readiness-summary" in layout_json
    assert "panel-readiness-table" in layout_json
    assert "Analysis preset" in layout_json
    assert "plot-preset" in layout_json
    assert "Apply Preset" in layout_json
    assert "plot-preset-table" in layout_json
    assert "channel-transform-overrides-store" in layout_json
    assert "transform-override-channel" in layout_json
    assert "transform-override-mode" in layout_json
    assert "apply-transform-override" in layout_json
    assert "clear-transform-override" in layout_json
    assert "transform-overrides-table" in layout_json
    assert "role-override-channel" in layout_json
    assert "role-override-value" in layout_json
    assert "Apply Role Override" in layout_json
    assert "Dropdown(id='role-override-value', value='fluorescence'" not in layout_json
    assert any("active-analysis-strip.children" in key for key in dash_app.callback_map)
    assert "analysis-guide.children" in dash_app.callback_map
    assert any("plot-context-bar.children" in key for key in dash_app.callback_map)
    assert any("panel-readiness-summary.children" in key for key in dash_app.callback_map)
    assert "panel-template-download.data" in dash_app.callback_map
    assert any("plot-preset.options" in key for key in dash_app.callback_map)
    assert any("plot-preset-status.children" in key for key in dash_app.callback_map)
    assert any("role-override-status.children" in key for key in dash_app.callback_map)
    assert any("channel-transform-overrides-store.data" in key for key in dash_app.callback_map)
    assert "role-override-value.value" in dash_app.callback_map
    assert any("analysis-revision-store.data" in key for key in dash_app.callback_map)
