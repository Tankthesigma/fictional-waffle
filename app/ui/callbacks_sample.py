from __future__ import annotations

import csv
from io import StringIO

from dash import Input, Output, State, html, no_update

from app.core.session_store import WorkbenchSession


def register_sample_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("selected-sample-store", "data"),
        Output("metadata-table", "data"),
        Output("channel-table", "data"),
        Output("x-channel", "options"),
        Output("y-channel", "options"),
        Output("hist-channel", "options"),
        Output("x-channel", "value"),
        Output("y-channel", "value"),
        Output("hist-channel", "value"),
        Output("active-analysis-strip", "children"),
        Output("channel-badge-rail", "children"),
        Output("panel-readiness-summary", "children"),
        Output("panel-readiness-table", "data"),
        Input("sample-dropdown", "value"),
        Input("sample-table", "selected_rows"),
        State("sample-table", "data"),
    )
    def select_sample(dropdown_value, selected_rows, sample_table_data):
        from app.core.channel_inference import best_scatter_pair
        from app.core.panel_setup import panel_readiness_rows, panel_readiness_summary

        selected = dropdown_value
        if selected_rows and sample_table_data:
            selected = sample_table_data[selected_rows[0]].get("sample_id")
        sample = session.selected_sample(selected)
        if not sample:
            return (
                None,
                [],
                [],
                [],
                [],
                [],
                None,
                None,
                None,
                _empty_analysis_strip(),
                _empty_channel_badges(),
                _panel_summary_cards(panel_readiness_summary(None)),
                [],
            )
        metadata_rows = [{"keyword": str(key), "value": str(value)} for key, value in sorted(sample.keywords.items())]
        channel_rows = [channel.to_dict() for channel in sample.channels]
        options = [{"label": channel.label, "value": channel.raw_name} for channel in sample.channels]
        x_default, y_default = best_scatter_pair(sample.channels)
        hist_default = sample.fluorescence_channels[0] if sample.fluorescence_channels else (sample.events.columns[0] if len(sample.events.columns) else None)
        return (
            sample.sample_id,
            metadata_rows,
            channel_rows,
            options,
            options,
            options,
            x_default,
            y_default,
            hist_default,
            _analysis_strip(sample, x_default, y_default, hist_default),
            _channel_badges(sample),
            _panel_summary_cards(panel_readiness_summary(sample)),
            panel_readiness_rows(sample),
        )

    @app.callback(
        Output("panel-template-download", "data"),
        Input("download-panel-template", "n_clicks"),
        State("selected-sample-store", "data"),
        prevent_initial_call=True,
    )
    def download_panel_template(_clicks, selected_sample):
        from app.core.panel_setup import PANEL_TEMPLATE_COLUMNS, panel_template_rows

        rows = panel_template_rows(session.selected_sample(selected_sample))
        if not rows:
            return no_update
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=PANEL_TEMPLATE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        return {
            "content": output.getvalue(),
            "filename": "ask-flow-panel-template.csv",
            "type": "text/csv",
        }


def _empty_analysis_strip():
    return [
        _bench_tile("Active sample", "No sample loaded", "Upload FCS or event-level CSV files to begin."),
        _bench_tile("Event matrix", "0 events", "Full-resolution statistics stay server-side."),
        _bench_tile("Default plot", "FSC / SSC pending", "Channels are inferred from metadata, then editable."),
        _bench_tile("Panel context", "No labels yet", "Optional panel CSV adds marker, antibody, and fluor labels."),
    ]


def _analysis_strip(sample, x_channel: str | None, y_channel: str | None, hist_channel: str | None):
    panel_labels = sum(1 for channel in sample.channels if channel.marker or channel.antibody or channel.fluorochrome)
    condition = sample.condition or "ungrouped"
    replicate = f"rep {sample.replicate}" if sample.replicate else "no replicate label"
    compensation = "compensation metadata available" if sample.compensated_events is not None else "raw view"
    return [
        _bench_tile("Active sample", sample.sample_id, f"{sample.filename} | {condition} | {replicate}"),
        _bench_tile("Event matrix", f"{sample.event_count:,} events", f"{sample.channel_count} channels | {len(sample.fluorescence_channels)} fluorescence"),
        _bench_tile("Default plot", f"{x_channel or 'Select X'} x {y_channel or 'Select Y'}", f"Histogram: {hist_channel or 'select channel'}"),
        _bench_tile("Panel context", f"{panel_labels} labeled channels", compensation),
    ]


def _bench_tile(label: str, value: str, detail: str):
    return html.Div([html.Span(label), html.Strong(value), html.Small(detail)], className="bench-tile")


def _empty_channel_badges():
    return [
        html.Div(
            [
                html.Span("Detector panel"),
                html.Strong("No channels loaded"),
                html.Small("Upload data to review inferred roles and panel labels."),
            ],
            className="channel-badge empty",
        )
    ]


def _channel_badges(sample):
    badges = []
    for channel in sample.channels:
        if not (
            channel.role == "fluorescence"
            or channel.role == "time"
            or channel.role.startswith("fsc")
            or channel.role.startswith("ssc")
        ):
            continue
        detail_parts = [part for part in [channel.antibody, channel.display_label] if part]
        detail = " | ".join(detail_parts) if detail_parts else channel.raw_name
        badges.append(
            html.Div(
                [
                    html.Span(channel.role),
                    html.Strong(channel.label),
                    html.Small(detail),
                ],
                className=f"channel-badge {channel.role.replace('-', '_')}",
            )
        )
    return badges or _empty_channel_badges()


def _panel_summary_cards(summary: dict[str, int | str]):
    return html.Div(
        [
            _panel_metric("Status", str(summary["status"]), "Map fluorescence markers before compare/report." if summary["status"] != "ready" else "Panel context is mapped."),
            _panel_metric("Fluorescence", str(summary["fluorescence_channels"]), f"{summary['labeled_fluorescence']} labeled"),
            _panel_metric("Needs Labels", str(summary["unlabeled_fluorescence"]), "Add marker/antibody/fluorochrome rows."),
            _panel_metric("Role Review", str(summary["unknown_channels"]), "Unknown channels should be checked."),
        ],
        className="panel-readiness-metrics",
    )


def _panel_metric(label: str, value: str, detail: str):
    return html.Div([html.Span(label), html.Strong(value), html.Small(detail)], className="panel-readiness-metric")
