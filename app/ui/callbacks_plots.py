from __future__ import annotations

import logging
from dash import Input, Output, State, html, no_update

from app.core.session_store import WorkbenchSession
from app.ui.components import table_columns

logger = logging.getLogger(__name__)


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
        Input("channel-transform-overrides-store", "data"),
        Input("gate-table", "data"),
    )
    def update_plot_context(sample_id, x_channel, y_channel, plot_mode, transform, max_events, compensation_enabled, transform_overrides, _gate_rows):
        from app.core.transform_settings import normalize_channel_overrides

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
        override_count = len(normalize_channel_overrides(transform_overrides))
        return [
            _context_chip("Sample", sample.sample_id, f"{display_events:,} displayed of {sample.event_count:,} events"),
            _context_chip("Axes", f"{_channel_label(sample, x_channel)} x {_channel_label(sample, y_channel)}", f"{plot_mode or 'scatter'} | {transform or 'raw'} | {event_view} | {override_count} override(s)"),
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
        Input("channel-transform-overrides-store", "data"),
        Input("gate-table", "data"),
    )
    def update_scatter(sample_id, x_channel, y_channel, plot_mode, transform, cofactor, max_events, compensation_enabled, transform_overrides, _gate_rows):
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
            channel_transform_overrides=transform_overrides,
        )

    @app.callback(
        Output("histogram-graph", "figure"),
        Input("hist-channel", "value"),
        Input("transform", "value"),
        Input("cofactor", "value"),
        Input("max-events", "value"),
        Input("compensation-enabled", "value"),
        Input("channel-transform-overrides-store", "data"),
    )
    def update_histogram(channel, transform, cofactor, max_events, compensation_enabled, transform_overrides):
        from app.core.plotting import histogram_figure

        return histogram_figure(
            session.sample_list(),
            channel,
            transform=transform or "raw",
            cofactor=cofactor or 150,
            max_events=max_events or 50_000,
            use_compensation=_is_compensation_on(compensation_enabled),
            channel_transform_overrides=transform_overrides,
        )

    @app.callback(
        Output("transform-override-channel", "options"),
        Input("selected-sample-store", "data"),
    )
    def update_transform_override_channels(sample_id):
        sample = session.selected_sample(sample_id)
        if not sample:
            return []
        return [{"label": channel.label, "value": channel.raw_name} for channel in sample.channels]

    @app.callback(
        Output("channel-transform-overrides-store", "data"),
        Output("transform-overrides-table", "data"),
        Output("transform-override-status", "children"),
        Input("apply-transform-override", "n_clicks"),
        Input("clear-transform-override", "n_clicks"),
        State("transform-override-channel", "value"),
        State("transform-override-mode", "value"),
        State("transform-override-cofactor", "value"),
        State("channel-transform-overrides-store", "data"),
        prevent_initial_call=True,
    )
    def update_channel_transform_override(_apply_clicks, _clear_clicks, channel, mode, cofactor, overrides):
        from dash import callback_context
        from app.core.transform_settings import SUPPORTED_TRANSFORMS, normalize_channel_overrides, override_rows

        action = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        current = normalize_channel_overrides(overrides)
        if not channel:
            return {"channel_overrides": current}, override_rows(current), "Choose a channel before changing an override."
        if action == "clear-transform-override":
            current.pop(str(channel), None)
            return {"channel_overrides": current}, override_rows(current), f"Cleared transform override for {channel}."
        transform = str(mode or "raw")
        if transform not in SUPPORTED_TRANSFORMS:
            return {"channel_overrides": current}, override_rows(current), "Choose a supported transform override."
        try:
            cofactor_value = max(float(cofactor or 150), 1.0)
        except (TypeError, ValueError):
            return {"channel_overrides": current}, override_rows(current), "Override cofactor must be numeric."
        current[str(channel)] = {"transform": transform, "cofactor": cofactor_value}
        return {"channel_overrides": current}, override_rows(current), f"Applied {transform} display override to {channel}."

    @app.callback(Output("event-count-chart", "figure"), Input("sample-ids-store", "data"))
    def update_event_counts(_sample_ids):
        from app.core.plotting import event_count_chart

        return event_count_chart(session.sample_list())

    @app.callback(Output("time-stability-graph", "figure"), Input("selected-sample-store", "data"))
    def update_time_stability(sample_id):
        from app.core.plotting import time_stability_figure

        return time_stability_figure(session.selected_sample(sample_id))

    @app.callback(
        Output("high-dimensional-graph", "figure"),
        Output("high-dimensional-cluster-table", "data"),
        Output("high-dimensional-cluster-table", "columns"),
        Input("selected-sample-store", "data"),
        Input("max-events", "value"),
    )
    def update_high_dimensional_review(sample_id, max_events):
        from app.core.high_dimensional import umap_cluster_review
        from app.core.plotting import high_dimensional_cluster_figure_from_review

        sample = session.selected_sample(sample_id)
        review = umap_cluster_review(sample, max_events=min(int(max_events or 25_000), 25_000))
        rows = review.clusters.to_dict("records") if not review.clusters.empty else []
        columns = _columns_from_rows(rows, ["cluster", "event_count", "percent_total"])
        sample_id_label = sample.sample_id if sample else "sample"
        return high_dimensional_cluster_figure_from_review(review, sample_id=sample_id_label), rows, table_columns(columns)

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

    @app.callback(
        Output("compensation-matrix-table", "data"),
        Output("compensation-matrix-table", "columns"),
        Input("selected-sample-store", "data"),
    )
    def update_compensation_matrix(sample_id):
        from app.core.compensation import spillover_matrix_rows

        sample = session.selected_sample(sample_id)
        if not sample:
            return [], table_columns(["channel"])
        rows = spillover_matrix_rows(sample)
        columns = ["channel", *[str(row["channel"]) for row in rows]]
        return rows, table_columns(columns)

    @app.callback(
        Output("compensation-status", "children", allow_duplicate=True),
        Output("compensation-enabled", "value", allow_duplicate=True),
        Input("apply-compensation-matrix", "n_clicks"),
        State("selected-sample-store", "data"),
        State("compensation-matrix-table", "data"),
        prevent_initial_call=True,
    )
    def apply_compensation_matrix(_clicks, sample_id, rows):
        from app.core.compensation import apply_manual_spillover

        sample = session.selected_sample(sample_id)
        if not sample:
            return "Upload and select a sample before editing compensation.", no_update
        try:
            warnings = apply_manual_spillover(sample, rows or [])
        except Exception as exc:
            logger.exception("Manual compensation matrix could not be applied for %s", sample.sample_id)
            return f"Compensation matrix was not applied: {exc}", no_update
        if sample.compensated_events is None:
            return "Compensation matrix was reviewed but not applied: " + " ".join(warnings), no_update
        warning_text = (" Review notes: " + " ".join(warnings)) if warnings else ""
        channel_count = len(sample.spillover.channels) if sample.spillover else 0
        return f"Applied user-reviewed compensation matrix for {channel_count} channel(s).{warning_text}", ["on"]


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
        and gate.gate_type in {"rectangle", "polygon", "ellipse", "quadrant", "bi_range"}
        and gate.channels[:2] == [x_channel, y_channel]
        and gate.metadata.get("event_view", "raw") == current_view
    )


def _columns_from_rows(rows: list[dict[str, object]], preferred: list[str]) -> list[str]:
    seen = list(preferred)
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen
