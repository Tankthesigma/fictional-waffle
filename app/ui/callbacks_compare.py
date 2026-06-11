from __future__ import annotations

from dash import Input, Output, State

from app.core.compare import batch_table, compare_control_treated, fluorescence_median_table
from app.core.session_store import WorkbenchSession
from app.ui.components import table_columns


def register_compare_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("batch-table", "data"),
        Output("median-table", "data"),
        Output("median-table", "columns"),
        Output("comparison-table", "data"),
        Input("sample-ids-store", "data"),
        Input("compare-button", "n_clicks"),
        Input("compensation-enabled", "value"),
        State("control-group", "value"),
        State("treated-group", "value"),
    )
    def update_compare(_sample_ids, _n_clicks, compensation_enabled, control_group, treated_group):
        samples = session.sample_list()
        use_compensation = isinstance(compensation_enabled, list) and "on" in compensation_enabled
        medians = fluorescence_median_table(samples, use_compensation=use_compensation)
        comparison_rows = []
        if control_group and treated_group:
            comparison_rows = [
                row.to_dict()
                for row in compare_control_treated(samples, control_group, treated_group, use_compensation=use_compensation)
            ]
            session.comparison_rows = comparison_rows
        median_columns = _columns_from_rows(medians, ["sample_id", "condition"])
        return batch_table(samples), medians, table_columns(median_columns), comparison_rows


def _columns_from_rows(rows: list[dict[str, object]], preferred: list[str]) -> list[str]:
    seen = list(preferred)
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen
