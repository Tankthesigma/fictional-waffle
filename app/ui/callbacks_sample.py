from __future__ import annotations

from dash import Input, Output, State, html

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
        Input("sample-dropdown", "value"),
        Input("sample-table", "selected_rows"),
        State("sample-table", "data"),
    )
    def select_sample(dropdown_value, selected_rows, sample_table_data):
        from app.core.channel_inference import best_scatter_pair

        selected = dropdown_value
        if selected_rows and sample_table_data:
            selected = sample_table_data[selected_rows[0]].get("sample_id")
        sample = session.selected_sample(selected)
        if not sample:
            return None, [], [], [], [], [], None, None, None, _empty_analysis_strip()
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
        )


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
