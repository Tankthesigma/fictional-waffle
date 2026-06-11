from __future__ import annotations

from dash import Input, Output, State, html, no_update

from app.core.session_store import WorkbenchSession


def register_plot_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("plot-preset", "options"),
        Output("plot-preset", "value"),
        Output("plot-preset-table", "data"),
        Input("selected-sample-store", "data"),
    )
    def update_plot_presets(sample_id):
        from app.core.plot_presets import plot_preset_rows, recommended_plot_presets

        sample = session.selected_sample(sample_id)
        presets = recommended_plot_presets(sample)
        return [preset.option() for preset in presets], presets[0].preset_id if presets else None, plot_preset_rows(sample)

    @app.callback(
        Output("x-channel", "value", allow_duplicate=True),
        Output("y-channel", "value", allow_duplicate=True),
        Output("hist-channel", "value", allow_duplicate=True),
        Output("plot-mode", "value"),
        Output("transform", "value"),
        Output("plot-preset-status", "children"),
        Input("apply-plot-preset", "n_clicks"),
        State("selected-sample-store", "data"),
        State("plot-preset", "value"),
        prevent_initial_call=True,
    )
    def apply_plot_preset(_clicks, sample_id, preset_id):
        from app.core.plot_presets import resolve_plot_preset

        sample = session.selected_sample(sample_id)
        preset = resolve_plot_preset(sample, preset_id)
        if preset is None:
            return no_update, no_update, no_update, no_update, no_update, "No compatible plot preset is available for the selected sample."
        return (
            preset.x_channel or no_update,
            preset.y_channel or no_update,
            preset.hist_channel or no_update,
            preset.plot_mode,
            preset.transform,
            f"Applied {preset.label}: {preset.description}",
        )

    @app.callback(
        Output("plot-context-bar", "children"),
        Input("selected-sample-store", "data"),
        Input("x-channel", "value"),
        Input("y-channel", "value"),
        Input("plot-mode", "value"),
        Input("transform", "value"),
        Input("max-events", "value"),
        Input("compensation-enabled", "value"),
        Input("gate-table", "data"),
    )
    def update_plot_context(sample_id, x_channel, y_channel, plot_mode, transform, max_events, compensation_enabled, _gate_rows):
        sample = session.selected_sample(sample_id)
        if not sample:
            return [
                _context_chip("Plot", "No active sample", "Upload data to populate the analysis workspace."),
                _context_chip("Display", "Awaiting channels", "FCS metadata and panel CSV labels appear here."),
            ]
        use_compensation = _is_compensation_on(compensation_enabled) and sample.compensated_events is not None
        event_view = "compensated" if use_compensation else "raw"
        display_events = min(sample.event_count, int(max_events or 50_000))
        gate_count = _visible_gate_count(session.gates, x_channel, y_channel, use_compensation)
        qc_count = len(session.qc_flags.get(sample.sample_id, []))
        return [
            _context_chip("Sample", sample.sample_id, f"{display_events:,} displayed of {sample.event_count:,} events"),
            _context_chip("Axes", f"{_channel_label(sample, x_channel)} x {_channel_label(sample, y_channel)}", f"{plot_mode or 'scatter'} | {transform or 'raw'} | {event_view}"),
            _context_chip("Gates", f"{gate_count} overlay(s)", "Only compatible enabled gates are drawn on this view."),
            _context_chip("Review", f"{qc_count} QC flag(s)", "Use QC tab for rule details and suggested checks."),
        ]

    @app.callback(
        Output("scatter-graph", "figure"),
        Input("selected-sample-store", "data"),
        Input("x-channel", "value"),
        Input("y-channel", "value"),
        Input("plot-mode", "value"),
        Input("transform", "value"),
        Input("cofactor", "value"),
        Input("max-events", "value"),
        Input("compensation-enabled", "value"),
        Input("gate-table", "data"),
    )
    def update_scatter(sample_id, x_channel, y_channel, plot_mode, transform, cofactor, max_events, compensation_enabled, _gate_rows):
        from app.core.plotting import scatter_figure

        sample = session.selected_sample(sample_id)
        return scatter_figure(
            sample,
            x_channel,
            y_channel,
            plot_mode=plot_mode or "scatter",
            transform=transform or "raw",
            cofactor=cofactor or 150,
            max_events=max_events or 50_000,
            gates=session.gates,
            use_compensation=_is_compensation_on(compensation_enabled),
        )

    @app.callback(
        Output("histogram-graph", "figure"),
        Input("hist-channel", "value"),
        Input("transform", "value"),
        Input("cofactor", "value"),
        Input("max-events", "value"),
        Input("compensation-enabled", "value"),
    )
    def update_histogram(channel, transform, cofactor, max_events, compensation_enabled):
        from app.core.plotting import histogram_figure

        return histogram_figure(
            session.sample_list(),
            channel,
            transform=transform or "raw",
            cofactor=cofactor or 150,
            max_events=max_events or 50_000,
            use_compensation=_is_compensation_on(compensation_enabled),
        )

    @app.callback(Output("event-count-chart", "figure"), Input("sample-ids-store", "data"))
    def update_event_counts(_sample_ids):
        from app.core.plotting import event_count_chart

        return event_count_chart(session.sample_list())

    @app.callback(Output("time-stability-graph", "figure"), Input("selected-sample-store", "data"))
    def update_time_stability(sample_id):
        from app.core.plotting import time_stability_figure

        return time_stability_figure(session.selected_sample(sample_id))

    @app.callback(Output("compensation-status", "children"), Input("selected-sample-store", "data"), Input("compensation-enabled", "value"))
    def update_compensation_status(sample_id, compensation_enabled):
        from app.core.compensation import compensation_status

        sample = session.selected_sample(sample_id)
        if not sample:
            return "Upload a sample to inspect compensation metadata."
        status = compensation_status(sample)
        if _is_compensation_on(compensation_enabled) and sample.compensated_events is None:
            return status + " Raw values remain displayed."
        if _is_compensation_on(compensation_enabled):
            return status + " Compensated view is active for plots and comparisons."
        return status


def _is_compensation_on(value) -> bool:
    return isinstance(value, list) and "on" in value


def _context_chip(label: str, value: str, detail: str):
    return html.Div([html.Span(label), html.Strong(value), html.Small(detail)], className="plot-context-chip")


def _channel_label(sample, raw_name: str | None) -> str:
    if not raw_name:
        return "Select channel"
    for channel in sample.channels:
        if channel.raw_name == raw_name:
            return channel.label
    return raw_name


def _visible_gate_count(gates, x_channel: str | None, y_channel: str | None, use_compensation: bool) -> int:
    if not x_channel or not y_channel:
        return 0
    current_view = "metadata_compensated" if use_compensation else "raw"
    return sum(
        1
        for gate in gates
        if gate.enabled
        and gate.gate_type == "rectangle"
        and gate.channels[:2] == [x_channel, y_channel]
        and gate.metadata.get("event_view", "raw") == current_view
    )
