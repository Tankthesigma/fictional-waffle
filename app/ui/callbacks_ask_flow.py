from __future__ import annotations

from dash import Input, Output, State, html

from app.core.session_store import WorkbenchSession


def register_ask_flow_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("ask-flow-briefing", "children"),
        Input("selected-sample-store", "data"),
        Input("x-channel", "value"),
        Input("y-channel", "value"),
        Input("gate-table", "data"),
        Input("comparison-table", "data"),
    )
    def update_briefing(sample_id, x_channel, y_channel, _gate_rows, _comparison_rows):
        from app.core.ask_flow import analysis_briefing

        sample = session.selected_sample(sample_id)
        flags = session.qc_flags.get(sample.sample_id, []) if sample else []
        return _briefing_cards(
            analysis_briefing(
                sample,
                x_channel=x_channel,
                y_channel=y_channel,
                gates=session.gates,
                qc_flags=flags,
                comparison_rows=session.comparison_rows,
            )
        )

    @app.callback(
        Output("ask-flow-answer", "children"),
        Input("ask-flow-button", "n_clicks"),
        State("ask-flow-question", "value"),
        State("selected-sample-store", "data"),
        State("x-channel", "value"),
        State("y-channel", "value"),
        prevent_initial_call=True,
    )
    def ask_flow(_clicks, question, sample_id, x_channel, y_channel):
        from app.core.ask_flow import answer_question

        sample = session.selected_sample(sample_id)
        flags = session.qc_flags.get(sample.sample_id, []) if sample else []
        return answer_question(
            question or "",
            sample,
            x_channel=x_channel,
            y_channel=y_channel,
            gates=session.gates,
            qc_flags=flags,
            comparison_rows=session.comparison_rows,
        )


def _briefing_cards(rows: list[dict[str, str]]):
    return [
        html.Div(
            [
                html.Span(row["status"]),
                html.Strong(row["title"]),
                html.P(row["body"]),
                html.Small(row["detail"]),
            ],
            className=f"ask-briefing-card {row['status']}",
        )
        for row in rows
    ]
