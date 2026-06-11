from __future__ import annotations

from dash import Input, Output, State

from app.core.channel_inference import best_scatter_pair
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
        Input("sample-dropdown", "value"),
        Input("sample-table", "selected_rows"),
        State("sample-table", "data"),
    )
    def select_sample(dropdown_value, selected_rows, sample_table_data):
        selected = dropdown_value
        if selected_rows and sample_table_data:
            selected = sample_table_data[selected_rows[0]].get("sample_id")
        sample = session.selected_sample(selected)
        if not sample:
            return None, [], [], [], [], [], None, None, None
        metadata_rows = [{"keyword": str(key), "value": str(value)} for key, value in sorted(sample.keywords.items())]
        channel_rows = [channel.to_dict() for channel in sample.channels]
        options = [{"label": channel.raw_name, "value": channel.raw_name} for channel in sample.channels]
        x_default, y_default = best_scatter_pair(sample.channels)
        hist_default = sample.fluorescence_channels[0] if sample.fluorescence_channels else (sample.events.columns[0] if len(sample.events.columns) else None)
        return sample.sample_id, metadata_rows, channel_rows, options, options, options, x_default, y_default, hist_default
