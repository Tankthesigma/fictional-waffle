from __future__ import annotations

from dash import Input, Output, State, html, no_update

from app.core.session_store import WorkbenchSession


def register_ask_flow_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("ask-flow-briefing", "children"),
        Output("ask-flow-plan", "children"),
        Output("ask-flow-agent-status", "children"),
        Input("selected-sample-store", "data"),
        Input("x-channel", "value"),
        Input("y-channel", "value"),
        Input("gate-table", "data"),
        Input("comparison-table", "data"),
    )
    def update_briefing(sample_id, x_channel, y_channel, _gate_rows, _comparison_rows):
        from app.core.ask_flow import analysis_briefing, analysis_plan
        from app.core.vertex_gemini import vertex_status

        sample = session.selected_sample(sample_id)
        flags = session.qc_flags.get(sample.sample_id, []) if sample else []
        return (
            _briefing_cards(
                analysis_briefing(
                    sample,
                    x_channel=x_channel,
                    y_channel=y_channel,
                    gates=session.gates,
                    qc_flags=flags,
                    comparison_rows=session.comparison_rows,
                )
            ),
            _plan_cards(
                analysis_plan(
                    sample,
                    gates=session.gates,
                    qc_flags=flags,
                    comparison_rows=session.comparison_rows,
                )
            ),
            vertex_status(),
        )

    @app.callback(
        Output("ask-flow-answer", "children"),
        Output("sample-dropdown", "value", allow_duplicate=True),
        Output("x-channel", "value", allow_duplicate=True),
        Output("y-channel", "value", allow_duplicate=True),
        Output("hist-channel", "value", allow_duplicate=True),
        Output("plot-mode", "value", allow_duplicate=True),
        Output("transform", "value", allow_duplicate=True),
        Output("max-events", "value", allow_duplicate=True),
        Input("ask-flow-button", "n_clicks"),
        State("ask-flow-question", "value"),
        State("selected-sample-store", "data"),
        State("x-channel", "value"),
        State("y-channel", "value"),
        prevent_initial_call=True,
    )
    def ask_flow(_clicks, question, sample_id, x_channel, y_channel):
        from app.core.ask_flow import answer_question
        from app.core.ask_flow_actions import plan_actions
        from app.core.vertex_gemini import answer_with_gemini

        sample = session.selected_sample(sample_id)
        plan = plan_actions(question or "", session.sample_list(), sample)
        if plan.updates.get("sample_id"):
            sample = session.selected_sample(plan.updates["sample_id"])
        flags = session.qc_flags.get(sample.sample_id, []) if sample else []
        fallback = answer_question(
            question or "",
            sample,
            x_channel=plan.updates.get("x_channel", x_channel),
            y_channel=plan.updates.get("y_channel", y_channel),
            gates=session.gates,
            qc_flags=flags,
            comparison_rows=session.comparison_rows,
        )
        gemini = answer_with_gemini(
            question or "",
            sample,
            fallback=fallback,
            x_channel=plan.updates.get("x_channel", x_channel),
            y_channel=plan.updates.get("y_channel", y_channel),
            gates=session.gates,
            qc_flags=flags,
            comparison_rows=session.comparison_rows,
            action_messages=plan.messages,
        )
        return (
            _answer_panel(gemini.text, gemini.status, plan.messages),
            plan.updates.get("sample_id", no_update),
            plan.updates.get("x_channel", no_update),
            plan.updates.get("y_channel", no_update),
            plan.updates.get("hist_channel", no_update),
            plan.updates.get("plot_mode", no_update),
            plan.updates.get("transform", no_update),
            plan.updates.get("max_events", no_update),
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


def _plan_cards(rows: list[dict[str, str]]):
    return [
        html.Div(
            [
                html.Span(row["status"]),
                html.Strong(row["title"]),
                html.P(row["body"]),
                html.Small(row["detail"]),
            ],
            className=f"analysis-plan-card {row['status']}",
        )
        for row in rows
    ]


def _answer_panel(answer: str, status: str, action_messages: list[str]):
    children = []
    if action_messages:
        children.append(
            html.Div(
                [html.Strong("Actions applied"), html.Ul([html.Li(message) for message in action_messages])],
                className="assistant-actions",
            )
        )
    children.extend([html.P(answer), html.Small(status)])
    return children
