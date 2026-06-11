from __future__ import annotations

from dash import dcc, html

from app.ui.components import card, data_table, metric_card, upload_box


def build_layout():
    return html.Div(
        [
            dcc.Store(id="sample-ids-store", data=[]),
            dcc.Store(id="selected-sample-store"),
            header(),
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
                    html.P("Local-only cytometry analysis", className="eyebrow"),
                    html.H1("Ask Flow Workbench"),
                    html.P(
                        "Exploratory only; does not control cytometer hardware and does not replace expert review.",
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


def home_upload_panel():
    return html.Section(
        [
            card(
                "Upload",
                [
                    html.P("Use exported FCS files when available. CSV fallback is supported for event-level tables with clear limitations.", className="muted"),
                    upload_box("upload-data", ".fcs or .csv files", multiple=True),
                    upload_box("upload-manifest", "Optional manifest CSV", multiple=False),
                    upload_box("upload-panel", "Optional panel setup CSV", multiple=False),
                    html.Button("Clear Project", id="clear-project", n_clicks=0),
                    html.Div(id="upload-status", className="status-box"),
                ],
                "upload-card",
            ),
            card(
                "Samples",
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
                    html.H2("Analysis Queue"),
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
                    data_table("gate-table", ["gate_id", "name", "type", "parent", "channels", "status", "enabled", "notes"], page_size=6),
                ],
                className="sidebar left-sidebar",
            ),
            html.Section(
                [
                    html.Div(id="active-analysis-strip", className="bench-strip"),
                    dcc.Tabs(
                        id="main-tabs",
                        value="explore",
                        children=[
                            dcc.Tab(label="Explore", value="explore", children=explore_tab()),
                            dcc.Tab(label="Gates", value="gates", children=gates_tab()),
                            dcc.Tab(label="Compare", value="compare", children=compare_tab()),
                            dcc.Tab(label="QC", value="qc", children=qc_tab()),
                            dcc.Tab(label="Reports", value="reports", children=reports_tab()),
                            dcc.Tab(label="Ask Flow", value="ask-flow", children=ask_flow_tab()),
                        ],
                    )
                ],
                className="center-panel",
            ),
            html.Aside(
                [
                    html.H2("Plot Settings"),
                    html.Div(
                        [
                            html.Span("Display stack", className="panel-kicker"),
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
                    html.Label("Compensation"),
                    dcc.Checklist(
                        id="compensation-enabled",
                        options=[{"label": "Use FCS spillover compensation when available", "value": "on"}],
                        value=[],
                        className="checklist",
                    ),
                    html.Div(id="compensation-status", className="status-box small"),
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


def explore_tab():
    return html.Div(
        [
            dcc.Graph(id="scatter-graph", config={"displayModeBar": True}, className="analysis-graph primary-graph"),
            dcc.Graph(id="histogram-graph", config={"displayModeBar": True}, className="analysis-graph"),
            html.Div(
                [
                    card("Metadata Inspector", data_table("metadata-table", ["keyword", "value"], page_size=8)),
                    card(
                        "Channel Inspector",
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
                                    html.Button("Suggest Candidate Gates", id="suggest-candidate-gates", n_clicks=0),
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
                                    html.Div(id="gate-status", className="status-box small"),
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
                        "Gate Manager",
                        [
                            html.Div("Rename, enable/disable, or delete one selected gate. Deleting a parent gate leaves child gates needing review.", className="muted"),
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
                    card("Gate Statistics", data_table("gate-stats-table", ["gate_name", "parent_gate", "channels", "event_count", "percent_total", "percent_parent"], page_size=12)),
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
                    html.Div(
                        [
                            html.Label("Control group"),
                            dcc.Input(id="control-group", type="text", placeholder="e.g. untreated"),
                            html.Label("Treated group"),
                            dcc.Input(id="treated-group", type="text", placeholder="e.g. treated"),
                            html.Button("Compare Groups", id="compare-button", n_clicks=0, className="primary"),
                            html.Button("Export Comparison CSV", id="export-comparison-csv", n_clicks=0),
                        ],
                        className="compare-form",
                    ),
                    html.Div(id="compare-status", className="status-box small"),
                    html.Div(id="compare-summary-cards", className="metrics-row compare-summary"),
                    dcc.Graph(id="event-count-chart"),
                    data_table("batch-table", ["sample_id", "condition", "replicate", "control_type", "event_count", "fluorescence_channels", "file_type"]),
                    data_table("median-table", ["sample_id", "condition"]),
                    data_table("comparison-table", ["channel", "control_median", "treated_median", "median_difference", "fold_change", "n_control", "n_treated", "notes"]),
                ],
            )
        ]
    )


def qc_tab():
    return html.Div(
        [
            card("QC Dashboard", [html.Div(id="qc-summary-cards", className="metrics-row"), data_table("qc-table", ["sample_id", "severity", "code", "title", "metric_value", "threshold", "suggested_check", "affects", "channel"])]),
            dcc.Graph(id="time-stability-graph"),
        ]
    )


def reports_tab():
    return html.Div(
        [
            card(
                "Report Builder",
                [
                    html.P("Exports are local files written to exports/. Static figures are included when the local Plotly image renderer is available.", className="muted"),
                    html.Button("Export PDF", id="export-pdf", n_clicks=0, className="primary"),
                    html.Button("Export PowerPoint", id="export-pptx", n_clicks=0),
                    html.Div(id="report-status", className="status-box"),
                ],
            )
        ]
    )


def ask_flow_tab():
    return html.Div(
        [
            card(
                "Ask Flow",
                [
                    html.P("Local deterministic summaries only. No cloud call, no API key, no diagnostic claims.", className="muted"),
                    dcc.Textarea(id="ask-flow-question", value="Summarize the QC flags.", className="ask-input"),
                    html.Button("Ask", id="ask-flow-button", n_clicks=0, className="primary"),
                    html.Div(id="ask-flow-answer", className="assistant-answer"),
                ],
            )
        ]
    )
