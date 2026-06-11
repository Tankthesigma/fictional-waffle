from __future__ import annotations

from dash import Input, Output

from app.core.compensation import compensation_status
from app.core.plotting import event_count_chart, histogram_figure, scatter_figure, time_stability_figure
from app.core.session_store import WorkbenchSession


def register_plot_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("scatter-graph", "figure"),
        Input("selected-sample-store", "data"),
        Input("x-channel", "value"),
        Input("y-channel", "value"),
        Input("transform", "value"),
        Input("cofactor", "value"),
        Input("max-events", "value"),
        Input("compensation-enabled", "value"),
        Input("gate-table", "data"),
    )
    def update_scatter(sample_id, x_channel, y_channel, transform, cofactor, max_events, compensation_enabled, _gate_rows):
        sample = session.selected_sample(sample_id)
        return scatter_figure(
            sample,
            x_channel,
            y_channel,
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
        return event_count_chart(session.sample_list())

    @app.callback(Output("time-stability-graph", "figure"), Input("selected-sample-store", "data"))
    def update_time_stability(sample_id):
        return time_stability_figure(session.selected_sample(sample_id))

    @app.callback(Output("compensation-status", "children"), Input("selected-sample-store", "data"), Input("compensation-enabled", "value"))
    def update_compensation_status(sample_id, compensation_enabled):
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
