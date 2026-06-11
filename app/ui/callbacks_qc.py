from __future__ import annotations

from dash import Input, Output, html

from app.core.session_store import WorkbenchSession


def register_qc_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("qc-table", "data"),
        Output("qc-cards", "children"),
        Output("qc-summary-cards", "children"),
        Input("sample-ids-store", "data"),
        Input("selected-sample-store", "data"),
    )
    def update_qc(_sample_ids, selected_sample):
        flags = session.all_qc_flags()
        selected_flags = session.qc_flags.get(selected_sample, []) if selected_sample else flags
        cards = [_qc_card("Severe", sum(1 for flag in flags if flag.severity == "severe"), "severe"), _qc_card("Warnings", sum(1 for flag in flags if flag.severity == "warning"), "warning"), _qc_card("Info", sum(1 for flag in flags if flag.severity == "info"), "info")]
        selected_cards = [_small_flag(flag) for flag in selected_flags[:6]] or [html.Div("No selected-sample QC flags.", className="flag-card")]
        return [flag.to_dict() for flag in flags], selected_cards, cards


def _qc_card(label: str, count: int, tone: str):
    return html.Div([html.Span(label), html.Strong(str(count))], className=f"metric {tone}")


def _small_flag(flag):
    return html.Div([html.Strong(flag.title), html.P(flag.suggested_check)], className=f"flag-card {flag.severity}")
