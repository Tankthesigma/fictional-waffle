from __future__ import annotations

from dash import dcc, html

from app.ui.components import card, data_table, metric_card, upload_box
from app.ui.plot_config import GATING_CONFIG, PLOT_CONFIG


def build_layout():
    return html.Div(
        [
            dcc.Store(id="sample-ids-store", data=[]),
            dcc.Store(id="selected-sample-store"),
            dcc.Store(id="analysis-revision-store", data=0),
            dcc.Store(id="last-drawn-gate-store"),
            dcc.Store(id="channel-transform-overrides-store", data={}),
            dcc.Store(id="ask-flow-command-history-store", data=[]),
            dcc.Store(id="toast-store"),
            dcc.Interval(id="toast-timer", interval=3500, disabled=True),
            html.Div(id="toast-container", className="toast-container"),
            header(),
            workspace_toolbar(),
            html.Main(
                [
                    home_upload_panel(),
                    workbench_panel(),
                ],
                className="app-shell",
            ),
        ]
    )


def header():
    return html.Header(
        [
            html.Div(
                [
                    html.P("FCS / CSV analysis workstation", className="eyebrow"),
                    html.H1("Ask Flow Workbench"),
                    html.P(
                        "Post-acquisition research review | no cytometer control | expert review required.",
                        className="safety-line",
                    ),
                    html.Div(
                        [
                            html.Span("Import"),
                            html.Span("Inspect"),
                            html.Span("Gate"),
                            html.Span("Compare"),
                            html.Span("Report"),
                        ],
                        className="workflow-strip",
                    ),
                ]
            ),
            html.Div(
                [
                    metric_card("Samples", "metric-samples"),
                    metric_card("Events", "metric-events"),
                    metric_card("Review Flags", "metric-flags"),
                ],
                className="metrics-row",
            ),
        ],
        className="topbar",
    )


def workspace_toolbar():
    return html.Nav(
        [
            html.Div(
                [
                    html.Span("Workspace"),
                    html.Strong("Local session"),
                ],
                className="toolbar-cell",
            ),
            html.Div(
                [
                    html.Span("Input"),
                    html.Strong("Exported FCS / CSV"),
                ],
                className="toolbar-cell",
            ),
            html.Div(
                [
                    html.Span("Events"),
                    html.Strong("Server-side matrices"),
                ],
                className="toolbar-cell",
            ),
            html.Div(
                [
                    html.Span("Review"),
                    html.Strong("Gates, QC, statistics"),
                ],
                className="toolbar-cell",
            ),
            html.Div(
                [
                    html.Span("Output"),
                    html.Strong("CSV / PDF / PPTX"),
                ],
                className="toolbar-cell",
            ),
        ],
        className="workspace-toolbar",
    )


def home_upload_panel():
    return html.Section(
        [
            card(
                "Import Queue",
                [
                    html.P("Use exported FCS files when available. CSV fallback is supported for event-level tables with clear limitations.", className="muted"),
                    upload_box("upload-data", ".fcs or .csv files", multiple=True),
                    upload_box("upload-manifest", "Optional manifest CSV", multiple=False),
                    upload_box("upload-panel", "Optional panel setup CSV", multiple=False),
                    html.Button("Download Panel Template", id="download-panel-template", n_clicks=0),
                    dcc.Download(id="panel-template-download"),
                    html.Button("Load Demo Dataset", id="load-demo-data", n_clicks=0, className="primary"),
                    html.Button("Clear Project", id="clear-project", n_clicks=0),
                    html.Div(id="upload-status", className="status-box"),
                ],
                "upload-card",
            ),
            card(
                "Sample Manager",
                data_table(
                    "sample-table",
                    [
                        "sample_id",
                        "filename",
                        "event_count",
                        "fcs_version",
                        "channel_count",
                        "primary_fsc",
                        "primary_ssc",
                        "time_channel",
                        "fluorescence_channels",
                        "qc_status",
                        "condition",
                        "replicate",
                    ],
                    row_selectable="single",
                    selected_rows=[],
                ),
            ),
        ],
        className="upload-grid",
    )


def workbench_panel():
    return html.Section(
        [
            html.Aside(
                [
                    html.H2("Workspace Tree"),
                    dcc.Dropdown(id="sample-dropdown", options=[], placeholder="Select sample", clearable=False),
                    html.Div(
                        [
                            html.Span("Population workflow"),
                            html.Ol(
                                [
                                    html.Li("Total events"),
                                    html.Li("Scatter cleanup"),
                                    html.Li("Fluorescence gate"),
                                    html.Li("Compare/export"),
                                ]
                            ),
                        ],
                        className="workflow-card",
                    ),
                    html.H2("Gate Tree"),
                    data_table("gate-table", ["gate_color", "gate_id", "name", "type", "parent", "channels", "status", "enabled", "notes"], page_size=6, hidden_columns=["gate_color"]),
                    html.Div("No gates yet. Add or suggest review-needed gates.", id="gate-stack-cards", className="gate-stack"),
                ],
                className="sidebar left-sidebar",
            ),
            html.Section(
                [
                    html.Div(id="active-analysis-strip", className="bench-strip"),
                    html.Div(id="analysis-guide", className="analysis-guide"),
                    global_assistant_bar(),
                    dcc.Tabs(
                        id="main-tabs",
                        value="explore",
                        className="wb-tabs",
                        children=[
                            dcc.Tab(
                                label="Explore",
                                value="explore",
                                className="wb-tab",
                                selected_className="wb-tab--selected",
                                children=explore_tab(),
                            ),
                            dcc.Tab(
                                label="Gates",
                                value="gates",
                                className="wb-tab",
                                selected_className="wb-tab--selected",
                                children=gates_tab(),
                            ),
                            dcc.Tab(
                                label="Compare",
                                value="compare",
                                className="wb-tab",
                                selected_className="wb-tab--selected",
                                children=compare_tab(),
                            ),
                            dcc.Tab(
                                label="QC",
                                value="qc",
                                className="wb-tab",
                                selected_className="wb-tab--selected",
                                children=qc_tab(),
                            ),
                            dcc.Tab(
                                label="Reports",
                                value="reports",
                                className="wb-tab",
                                selected_className="wb-tab--selected",
                                children=reports_tab(),
                            ),
                            dcc.Tab(
                                label="Ask Flow",
                                value="ask-flow",
                                className="wb-tab",
                                selected_className="wb-tab--selected",
                                children=ask_flow_tab(),
                            ),
                        ],
                    )
                ],
                className="center-panel",
            ),
            html.Aside(
                [
                    html.H2("Plot Inspector"),
                    html.Div(
                        [
                            html.Span("Data view", className="panel-kicker"),
                            html.Div(
                                [
                                    html.Span("Raw data preserved"),
                                    html.Span("Transforms display-only"),
                                    html.Span("Stats use full matrix"),
                                ],
                                className="mode-chips",
                            ),
                        ],
                        className="settings-primer",
                    ),
                    html.Label("Analysis preset"),
                    dcc.Dropdown(id="plot-preset", options=[], placeholder="Recommended plot setup", clearable=True),
                    html.Button("Apply Preset", id="apply-plot-preset", n_clicks=0),
                    html.Div(id="plot-preset-status", className="status-box small"),
                    data_table("plot-preset-table", ["preset", "scatter", "histogram", "mode", "transform", "why"], page_size=4),
                    html.Label("X channel"),
                    dcc.Dropdown(id="x-channel"),
                    html.Label("Y channel"),
                    dcc.Dropdown(id="y-channel"),
                    html.Label("Plot mode"),
                    dcc.Dropdown(
                        id="plot-mode",
                        value="scatter",
                        clearable=False,
                        options=[
                            {"label": "Dot plot", "value": "scatter"},
                            {"label": "Density plot", "value": "density"},
                            {"label": "Contour plot", "value": "contour"},
                        ],
                    ),
                    html.Label("Histogram channel"),
                    dcc.Dropdown(id="hist-channel"),
                    html.Label("Transform"),
                    dcc.Dropdown(
                        id="transform",
                        value="raw",
                        clearable=False,
                        options=[
                            {"label": "Raw / linear", "value": "raw"},
                            {"label": "Safe log10", "value": "safe_log10"},
                            {"label": "Arcsinh", "value": "arcsinh"},
                            {"label": "Logicle if available", "value": "logicle"},
                        ],
                    ),
                    html.Label("Arcsinh cofactor"),
                    dcc.Input(id="cofactor", type="number", value=150, min=1, step=1),
                    html.Label("Per-channel transform override"),
                    dcc.Dropdown(id="transform-override-channel", options=[], placeholder="Channel override", clearable=True),
                    dcc.Dropdown(
                        id="transform-override-mode",
                        value="arcsinh",
                        clearable=False,
                        options=[
                            {"label": "Raw / linear", "value": "raw"},
                            {"label": "Safe log10", "value": "safe_log10"},
                            {"label": "Arcsinh", "value": "arcsinh"},
                            {"label": "Logicle if available", "value": "logicle"},
                        ],
                    ),
                    dcc.Input(id="transform-override-cofactor", type="number", value=150, min=1, step=1),
                    html.Div(
                        [
                            html.Button("Apply Channel Transform", id="apply-transform-override", n_clicks=0),
                            html.Button("Clear Channel Transform", id="clear-transform-override", n_clicks=0),
                        ],
                        className="button-row",
                    ),
                    html.Div(id="transform-override-status", className="status-box small"),
                    data_table("transform-overrides-table", ["channel", "transform", "cofactor"], page_size=4),
                    html.Label("Compensation"),
                    dcc.Checklist(
                        id="compensation-enabled",
                        options=[{"label": "Use FCS spillover compensation when available", "value": "on"}],
                        value=[],
                        className="checklist",
                    ),
                    html.Div(id="compensation-status", className="status-box small"),
                    data_table("compensation-matrix-table", ["channel"], page_size=6, editable=True),
                    html.Button("Apply Compensation Matrix", id="apply-compensation-matrix", n_clicks=0),
                    html.Label("Max plotted events"),
                    dcc.Input(id="max-events", type="number", value=50_000, min=1_000, step=1_000),
                    html.H2("QC Cards"),
                    html.Div(id="qc-cards", className="qc-cards"),
                ],
                className="sidebar right-sidebar",
            ),
        ],
        className="workbench-grid",
    )


def global_assistant_bar():
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Ask Flow", className="panel-kicker"),
                    html.Strong("Workbench copilot"),
                    html.Small("Ask from any tab. It can navigate, set plots, adjust transforms, and create review-needed gates."),
                ],
                className="global-assistant-copy",
            ),
            html.Div(
                [
                    dcc.Input(
                        id="global-assistant-command",
                        placeholder="Try: show QC, plot CD3 vs SSC-A as density, create singlet gate, auto gate clusters",
                        debounce=False,
                    ),
                    html.Button("Run", id="global-assistant-button", n_clicks=0, className="primary"),
                ],
                className="global-assistant-command-row",
            ),
            html.Div(
                [
                    html.Button("Analyze", id="global-quick-analyze", n_clicks=0),
                    html.Button("QC", id="global-quick-qc", n_clicks=0),
                    html.Button("Singlets", id="global-quick-singlets", n_clicks=0),
                    html.Button("Cluster gates", id="global-quick-cluster-gates", n_clicks=0),
                    html.Button("Report", id="global-quick-report", n_clicks=0),
                ],
                className="global-assistant-quick-actions",
            ),
            html.Div(
                [
                    html.Span("Skills"),
                    html.Span("navigate"),
                    html.Span("plot"),
                    html.Span("histogram"),
                    html.Span("transform"),
                    html.Span("singlets"),
                    html.Span("cluster gates"),
                    html.Span("approve/reject"),
                    html.Span("summarize"),
                ],
                className="agent-action-strip global-skills",
            ),
            dcc.Loading(
                id="global-assistant-loading",
                type="dot",
                color="#0f766e",
                delay_show=150,
                children=html.Div(id="global-assistant-answer", className="global-assistant-answer"),
            ),
            html.Div(id="global-assistant-timeline", className="global-assistant-timeline"),
        ],
        className="global-assistant-bar",
    )


def explore_tab():
    return html.Div(
        [
            html.Div(id="plot-context-bar", className="plot-context-bar"),
            dcc.Graph(
                id="scatter-graph",
                config=GATING_CONFIG,
                className="analysis-graph primary-graph",
            ),
            dcc.Graph(id="histogram-graph", config=PLOT_CONFIG, className="analysis-graph"),
            html.Div(id="channel-badge-rail", className="channel-badge-rail"),
            card(
                "Panel Setup Readiness",
                [
                    html.Div(id="panel-readiness-summary", className="panel-readiness-summary"),
                    data_table(
                        "panel-readiness-table",
                        ["channel", "display_label", "marker", "antibody", "fluorochrome", "role", "status", "next_step"],
                        page_size=8,
                    ),
                ],
                "panel-readiness-card",
            ),
            html.Div(
                [
                    card("Metadata Inspector", data_table("metadata-table", ["keyword", "value"], page_size=8)),
                    card(
                        "Channel Inspector",
                        [
                            html.Div(
                                [
                                    dcc.Dropdown(id="role-override-channel", options=[], placeholder="Channel to review", clearable=False),
                                    dcc.Dropdown(
                                        id="role-override-value",
                                        placeholder="Current role",
                                        clearable=False,
                                        options=[
                                            {"label": "FSC", "value": "fsc"},
                                            {"label": "FSC-A", "value": "fsc-a"},
                                            {"label": "FSC-H", "value": "fsc-h"},
                                            {"label": "FSC-W", "value": "fsc-w"},
                                            {"label": "SSC", "value": "ssc"},
                                            {"label": "SSC-A", "value": "ssc-a"},
                                            {"label": "SSC-H", "value": "ssc-h"},
                                            {"label": "SSC-W", "value": "ssc-w"},
                                            {"label": "Time", "value": "time"},
                                            {"label": "Fluorescence", "value": "fluorescence"},
                                            {"label": "Index", "value": "index"},
                                            {"label": "Unknown", "value": "unknown"},
                                        ],
                                    ),
                                    html.Button("Apply Role Override", id="apply-role-override", n_clicks=0),
                                ],
                                className="channel-override-form",
                            ),
                            html.Div(id="role-override-status", className="status-box small"),
                            data_table(
                                "channel-table",
                                [
                                    "index",
                                    "raw_name",
                                    "display_label",
                                    "marker",
                                    "antibody",
                                    "fluorochrome",
                                    "role",
                                    "min",
                                    "max",
                                    "p1",
                                    "p5",
                                    "median",
                                    "p95",
                                    "p99",
                                    "range",
                                    "percent_near_min",
                                    "percent_near_max",
                                    "notes",
                                ],
                                page_size=12,
                            ),
                        ],
                    ),
                ],
                className="two-col",
            ),
        ]
    )


def gates_tab():
    return html.Div(
        [
            html.Div(
                [
                    card(
                        "Rectangle Gate",
                        [
                            html.Div("Use the current X/Y channels. Enter raw-scale bounds; display transforms do not change stored events.", className="muted"),
                            html.Div(
                                [
                                    dcc.Input(id="gate-name", type="text", placeholder="Gate name", value="User rectangle gate"),
                                    dcc.Input(id="gate-x-min", type="number", placeholder="x min"),
                                    dcc.Input(id="gate-x-max", type="number", placeholder="x max"),
                                    dcc.Input(id="gate-y-min", type="number", placeholder="y min"),
                                    dcc.Input(id="gate-y-max", type="number", placeholder="y max"),
                                    html.Button("Add Rectangle Gate", id="add-rectangle-gate", n_clicks=0, className="primary"),
                                    html.Button("Quick Gate Current View", id="add-review-current-view-gate", n_clicks=0),
                                    html.Button("Add Review FSC/SSC Gate", id="add-review-scatter-gate", n_clicks=0),
                                    html.Button("Suggest Candidate Gates", id="suggest-candidate-gates", n_clicks=0),
                                    html.Button("Create Singlet Gate", id="create-singlet-gate", n_clicks=0),
                                    html.Button("Cluster-Guided Gate Review", id="ai-auto-gate-clusters", n_clicks=0),
                                    html.Button("Accept Candidates", id="accept-candidate-gates", n_clicks=0),
                                    html.Button("Reject Candidates", id="reject-candidate-gates", n_clicks=0),
                                ],
                                className="gate-form",
                            ),
                            html.Div(
                                "Candidate gates are review-needed and disabled until accepted; they are not biological conclusions.",
                                className="muted",
                            ),
                            html.Div(
                                [
                                    html.Button("Save Gates JSON", id="save-gates", n_clicks=0),
                                    html.Button("Load Gates JSON", id="load-gates", n_clicks=0),
                                    html.Button("Save Project JSON", id="save-project", n_clicks=0),
                                    html.Button("Load Project JSON", id="load-project", n_clicks=0),
                                    html.Button("Export Selected Gate as FCS", id="export-gated-fcs", n_clicks=0),
                                    html.Button("Export Selected Gate as CSV", id="export-gated-csv", n_clicks=0),
                                    html.Button("Save Analysis Template", id="save-analysis-template", n_clicks=0),
                                    html.Button("Load Analysis Template", id="load-analysis-template", n_clicks=0),
                                    html.Div(id="gate-status", className="status-box small"),
                                    html.Div(id="template-status", className="status-box small"),
                                ],
                                className="button-row",
                            ),
                        ],
                    ),
                    card(
                        "Histogram Range Gate",
                        [
                            html.Div("Use the current histogram channel. Enter raw-scale bounds; display transforms do not change stored events.", className="muted"),
                            html.Div(
                                [
                                    dcc.Input(id="hist-gate-name", type="text", placeholder="Gate name", value="User histogram gate"),
                                    dcc.Input(id="hist-gate-min", type="number", placeholder="min"),
                                    dcc.Input(id="hist-gate-max", type="number", placeholder="max"),
                                    html.Button("Add Histogram Gate", id="add-histogram-gate", n_clicks=0, className="primary"),
                                ],
                                className="gate-form",
                            ),
                        ],
                    ),
                    card(
                        "Quadrant / Ellipse / Bi-Range Gates",
                        [
                            html.Div("Use the current X/Y channels. Bounds are stored on raw event values; drawn/display transforms stay visual.", className="muted"),
                            html.Div(
                                [
                                    dcc.Input(id="quadrant-gate-name", type="text", placeholder="Quadrant name", value="Quadrant gate"),
                                    dcc.Input(id="quadrant-x-threshold", type="number", placeholder="x threshold"),
                                    dcc.Input(id="quadrant-y-threshold", type="number", placeholder="y threshold"),
                                    html.Button("Add Quadrants", id="add-quadrant-gates", n_clicks=0, className="primary"),
                                ],
                                className="gate-form",
                            ),
                            html.Div(
                                [
                                    dcc.Input(id="ellipse-gate-name", type="text", placeholder="Ellipse name", value="Ellipse gate"),
                                    dcc.Input(id="ellipse-center-x", type="number", placeholder="center x"),
                                    dcc.Input(id="ellipse-center-y", type="number", placeholder="center y"),
                                    dcc.Input(id="ellipse-radius-x", type="number", placeholder="radius x"),
                                    dcc.Input(id="ellipse-radius-y", type="number", placeholder="radius y"),
                                    html.Button("Add Ellipse", id="add-ellipse-gate", n_clicks=0),
                                ],
                                className="gate-form",
                            ),
                            html.Div(
                                [
                                    dcc.Input(id="birange-gate-name", type="text", placeholder="Bi-range name", value="Bi-range gate"),
                                    dcc.Input(id="birange-x-min", type="number", placeholder="x min"),
                                    dcc.Input(id="birange-x-max", type="number", placeholder="x max"),
                                    dcc.Input(id="birange-y-min", type="number", placeholder="y min"),
                                    dcc.Input(id="birange-y-max", type="number", placeholder="y max"),
                                    html.Button("Add Bi-Range", id="add-birange-gate", n_clicks=0),
                                ],
                                className="gate-form",
                            ),
                        ],
                    ),
                    card(
                        "Boolean Gate",
                        [
                            html.Div("Combine existing gates with AND, OR, or NOT. Boolean gates are review-needed and recomputed across samples.", className="muted"),
                            html.Div(
                                [
                                    dcc.Input(id="boolean-gate-name", type="text", placeholder="Gate name", value="Boolean population"),
                                    dcc.Dropdown(
                                        id="boolean-operation",
                                        value="AND",
                                        clearable=False,
                                        options=[
                                            {"label": "AND", "value": "AND"},
                                            {"label": "OR", "value": "OR"},
                                            {"label": "NOT", "value": "NOT"},
                                        ],
                                    ),
                                    dcc.Dropdown(id="boolean-gate-a", options=[], placeholder="First gate", clearable=False),
                                    dcc.Dropdown(id="boolean-gate-b", options=[], placeholder="Second gate for AND/OR", clearable=True),
                                    html.Button("Add Boolean Gate", id="add-boolean-gate", n_clicks=0),
                                ],
                                className="gate-form",
                            ),
                        ],
                    ),
                    card(
                        "Gate Manager",
                        [
                            html.Div("Rename, enable/disable, or delete one selected gate. Select a gate here before drawing on the plot to make the new drawn gate a child of it.", className="muted"),
                            html.Div(
                                [
                                    dcc.Dropdown(id="manage-gate-id", options=[], placeholder="Select gate", clearable=False),
                                    dcc.Input(id="manage-gate-name", type="text", placeholder="New gate name"),
                                    html.Button("Rename Gate", id="rename-gate", n_clicks=0),
                                    html.Button("Enable / Disable", id="toggle-gate", n_clicks=0),
                                    html.Button("Delete Gate", id="delete-gate", n_clicks=0),
                                ],
                                className="gate-form",
                            ),
                        ],
                    ),
                    card(
                        "Gate Statistics",
                        data_table(
                            "gate-stats-table",
                            ["gate_color", "gate_name", "parent_gate", "channels", "event_count", "percent_total", "percent_parent"],
                            page_size=12,
                            hidden_columns=["gate_color"],
                        ),
                    ),
                    html.Button("Export Gate Stats CSV", id="export-gate-stats", n_clicks=0),
                ],
                className="stack",
            )
        ]
    )


def compare_tab():
    return html.Div(
        [
            card(
                "Batch Comparison",
                [
                    html.Div(id="grouping-readiness-summary", className="grouping-readiness-summary"),
                    html.Div(
                        [
                            html.Button("Download Manifest Template", id="download-manifest-template", n_clicks=0),
                            dcc.Download(id="manifest-template-download"),
                        ],
                        className="button-row",
                    ),
                    data_table(
                        "grouping-readiness-table",
                        ["sample_id", "file_name", "condition", "replicate", "control_type", "status", "next_step"],
                        page_size=6,
                    ),
                    html.Div(
                        [
                            html.Label("Control group"),
                            dcc.Dropdown(id="control-group", options=[], placeholder="Select control group", clearable=True),
                            html.Label("Treated group"),
                            dcc.Dropdown(id="treated-group", options=[], placeholder="Select treated group", clearable=True),
                            html.Button("Compare Groups", id="compare-button", n_clicks=0, className="primary"),
                            html.Button("Apply Gates Across Batch", id="batch-apply-gates", n_clicks=0),
                            html.Button("Concatenate Loaded Samples", id="concatenate-samples", n_clicks=0),
                            html.Button("Export Concatenated FCS", id="export-concatenated-fcs", n_clicks=0),
                            html.Button("Export Comparison CSV", id="export-comparison-csv", n_clicks=0),
                            html.Button("Export Population Frequencies CSV", id="export-population-frequency-csv", n_clicks=0),
                        ],
                        className="compare-form",
                    ),
                    html.Div(id="compare-status", className="status-box small"),
                    html.Div(id="compare-summary-cards", className="metrics-row compare-summary"),
                    html.Div(id="compare-insights", className="compare-insights"),
                    dcc.Graph(id="comparison-delta-chart", config=PLOT_CONFIG),
                    dcc.Graph(id="event-count-chart", config=PLOT_CONFIG),
                    data_table("batch-table", ["sample_id", "condition", "replicate", "control_type", "event_count", "fluorescence_channels", "file_type"]),
                    data_table("median-table", ["sample_id", "condition"]),
                    data_table(
                        "batch-gate-stats-table",
                        ["sample_id", "condition", "replicate", "gate_name", "parent_gate", "event_count", "percent_total", "percent_parent", "gate_warning"],
                    ),
                    data_table("population-frequency-table", ["population", "parent_gate"], page_size=12),
                    data_table(
                        "comparison-table",
                        [
                            "channel",
                            "channel_label",
                            "control_median",
                            "treated_median",
                            "median_difference",
                            "fold_change",
                            "n_control",
                            "n_treated",
                            "notes",
                        ],
                    ),
                ],
            )
        ]
    )


def qc_tab():
    return html.Div(
        [
            card(
                "QC Dashboard",
                [
                    html.Div(id="qc-summary-cards", className="metrics-row"),
                    html.Div(id="qc-review-lanes", className="qc-review-lanes"),
                    data_table("qc-table", ["sample_id", "severity", "code", "title", "metric_value", "threshold", "suggested_check", "affects", "channel"]),
                ],
            ),
            dcc.Graph(id="time-stability-graph", config=PLOT_CONFIG),
        ]
    )


def reports_tab():
    return html.Div(
        [
            card(
                "Report Builder",
                [
                    html.P("Exports are local files written to exports/. Static figures are included when the local Plotly image renderer is available.", className="muted"),
                    dcc.Loading(
                        type="dot",
                        color="#0f766e",
                        children=[
                            html.Div(id="report-readiness", className="report-readiness"),
                            html.Div(id="report-outline-preview", className="report-outline-preview"),
                            html.Button("Export PDF", id="export-pdf", n_clicks=0, className="primary"),
                            html.Button("Export PowerPoint", id="export-pptx", n_clicks=0),
                            html.Div(id="report-status", className="status-box"),
                        ],
                    ),
                ],
            )
        ]
    )


def ask_flow_tab():
    return html.Div(
        [
            card(
                "Review Console",
                [
                    html.P("Analysis review console for plots, QC, gates, high-dimensional clusters, and report-ready summaries.", className="muted"),
                    html.Div(id="ask-flow-agent-status", className="status-box small"),
                    html.Div(id="ask-flow-briefing", className="ask-briefing"),
                    html.H3("Review Plan"),
                    html.Div(id="ask-flow-plan", className="analysis-plan-grid"),
                    html.H3("High-Dimensional Review"),
                    dcc.Loading(
                        type="dot",
                        color="#0f766e",
                        children=dcc.Graph(id="high-dimensional-graph", config=PLOT_CONFIG, className="analysis-graph"),
                    ),
                    data_table("high-dimensional-cluster-table", ["cluster", "event_count", "percent_total"], page_size=8),
                    dcc.Textarea(
                        id="ask-flow-question",
                        value="Plan the analysis for this sample.",
                        placeholder="Ask about the current analysis, or try: plot FL1-A vs SSC-A as density with arcsinh; histogram FITC; show 100000 events.",
                        className="ask-input",
                    ),
                    html.Button("Ask", id="ask-flow-button", n_clicks=0, className="primary"),
                    dcc.Loading(
                        id="ask-flow-loading",
                        type="circle",
                        color="#0f766e",
                        delay_show=150,
                        children=html.Div(id="ask-flow-loading-anchor", className="ask-loading-anchor"),
                    ),
                    html.Div(
                        [
                            html.Span("Workbench actions:"),
                            html.Span("set sample"),
                            html.Span("set axes"),
                            html.Span("set histogram"),
                            html.Span("plot mode"),
                            html.Span("transform"),
                            html.Span("max events"),
                            html.Span("cluster gate review"),
                        ],
                        className="agent-action-strip",
                    ),
                    dcc.Loading(
                        id="ask-flow-answer-loading",
                        type="default",
                        color="#0f766e",
                        delay_show=150,
                        children=html.Div(id="ask-flow-answer", className="assistant-answer"),
                    ),
                ],
            )
        ]
    )
