from __future__ import annotations

from dash import Input, Output, State, callback_context, html, no_update

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
        Output("global-assistant-answer", "children"),
        Output("main-tabs", "value", allow_duplicate=True),
        Output("sample-dropdown", "value", allow_duplicate=True),
        Output("x-channel", "value", allow_duplicate=True),
        Output("y-channel", "value", allow_duplicate=True),
        Output("hist-channel", "value", allow_duplicate=True),
        Output("plot-mode", "value", allow_duplicate=True),
        Output("transform", "value", allow_duplicate=True),
        Output("max-events", "value", allow_duplicate=True),
        Output("gate-table", "data", allow_duplicate=True),
        Output("gate-stats-table", "data", allow_duplicate=True),
        Output("gate-stats-table", "columns", allow_duplicate=True),
        Output("gate-status", "children", allow_duplicate=True),
        Output("manage-gate-id", "options", allow_duplicate=True),
        Output("manage-gate-id", "value", allow_duplicate=True),
        Output("gate-stack-cards", "children", allow_duplicate=True),
        Input("ask-flow-button", "n_clicks"),
        Input("global-assistant-button", "n_clicks"),
        Input("global-quick-qc", "n_clicks"),
        Input("global-quick-singlets", "n_clicks"),
        Input("global-quick-cluster-gates", "n_clicks"),
        Input("global-quick-report", "n_clicks"),
        State("ask-flow-question", "value"),
        State("global-assistant-command", "value"),
        State("selected-sample-store", "data"),
        State("x-channel", "value"),
        State("y-channel", "value"),
        State("compensation-enabled", "value"),
        prevent_initial_call=True,
    )
    def ask_flow(
        _ask_clicks,
        _global_clicks,
        _quick_qc,
        _quick_singlets,
        _quick_cluster_gates,
        _quick_report,
        tab_question,
        global_question,
        sample_id,
        x_channel,
        y_channel,
        compensation_enabled,
    ):
        from app.core.ask_flow import answer_question
        from app.core.ask_flow_actions import plan_actions
        from app.core.vertex_gemini import answer_with_gemini

        triggered = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        question = _question_from_trigger(triggered, tab_question, global_question)
        sample = session.selected_sample(sample_id)
        plan = plan_actions(question or "", session.sample_list(), sample)
        if plan.updates.get("sample_id"):
            sample = session.selected_sample(plan.updates["sample_id"])
        auto_gate_status = None
        auto_gate_outputs = _empty_gate_outputs()
        singlet_status = None
        if _requests_auto_gate(question or ""):
            auto_gate_status, auto_gate_outputs = _run_auto_gate_from_chat(
                session,
                sample,
                plan.updates.get("x_channel", x_channel),
                plan.updates.get("y_channel", y_channel),
                compensation_enabled,
            )
            plan.messages.append(auto_gate_status)
        elif _requests_singlet_gate(question or ""):
            singlet_status, auto_gate_outputs = _run_singlet_gate_from_chat(session, sample, compensation_enabled)
            plan.messages.append(singlet_status)
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
        answer_panel = _answer_panel(gemini.text, gemini.status, plan.messages)
        return (
            answer_panel,
            answer_panel,
            plan.updates.get("tab", no_update),
            plan.updates.get("sample_id", no_update),
            plan.updates.get("x_channel", no_update),
            plan.updates.get("y_channel", no_update),
            plan.updates.get("hist_channel", no_update),
            plan.updates.get("plot_mode", no_update),
            plan.updates.get("transform", no_update),
            plan.updates.get("max_events", no_update),
            *auto_gate_outputs,
        )


def _question_from_trigger(triggered: str, tab_question: str | None, global_question: str | None) -> str:
    quick_questions = {
        "global-quick-qc": "show QC and summarize the review flags",
        "global-quick-singlets": "create singlet gate",
        "global-quick-cluster-gates": "auto gate clusters",
        "global-quick-report": "open reports and draft a plain-English report paragraph",
    }
    if triggered in quick_questions:
        return quick_questions[triggered]
    if triggered == "global-assistant-button":
        return global_question or ""
    return tab_question or ""


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


def _requests_auto_gate(question: str) -> bool:
    normalized = question.lower()
    return any(phrase in normalized for phrase in ("auto gate", "autogate", "cluster gate", "ai gate", "suggest gates from clusters", "cluster-guided gate"))


def _requests_singlet_gate(question: str) -> bool:
    normalized = question.lower()
    return "singlet" in normalized and any(phrase in normalized for phrase in ("gate", "preset", "create", "make", "add", "suggest"))


def _empty_gate_outputs():
    return (no_update, no_update, no_update, no_update, no_update, no_update, no_update)


def _run_singlet_gate_from_chat(session: WorkbenchSession, sample, compensation_enabled):
    from uuid import uuid4

    from app.core.compensation import event_view
    from app.core.gating import gate_to_table, suggest_singlet_gate
    from app.ui.callbacks_gating import _columns_from_rows, _gate_options, _gate_stack_cards, _stats_for_sample
    from app.ui.components import table_columns

    if sample is None:
        return "Singlet preset skipped: select a sample first.", _empty_gate_outputs()
    use_compensation = bool(compensation_enabled and "on" in compensation_enabled and sample.compensated_events is not None)
    gate = suggest_singlet_gate(
        event_view(sample, use_compensation),
        sample.channels,
        uuid4().hex[:8],
    )
    if gate is None:
        return "Singlet preset skipped: no compatible area/height or area/width pulse-geometry pair was found.", _empty_gate_outputs()
    gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
    session.gates.append(gate)
    stats = _stats_for_sample(session, sample.sample_id, compensation_enabled)
    columns = _columns_from_rows(stats, ["gate_name", "parent_gate", "channel_labels", "channels", "event_count", "percent_total", "percent_parent"])
    options = _gate_options(session.gates)
    status = f"Added disabled review-needed singlet preset: {gate.name}. Review/edit and accept before using final statistics."
    return status, (
        gate_to_table(session.gates),
        stats,
        table_columns(columns),
        status,
        options,
        gate.gate_id,
        _gate_stack_cards(session.gates, stats),
    )


def _run_auto_gate_from_chat(session: WorkbenchSession, sample, x_channel, y_channel, compensation_enabled):
    from uuid import uuid4

    from app.core.auto_gating import suggest_ai_auto_gates
    from app.core.gating import gate_to_table
    from app.core.vertex_gemini import label_clusters_with_gemini
    from app.ui.callbacks_gating import _auto_gate_status, _columns_from_rows, _gate_options, _gate_stack_cards, _stats_for_sample
    from app.ui.components import table_columns

    if sample is None:
        return "Cluster gate review skipped: select a sample first.", _empty_gate_outputs()
    result = suggest_ai_auto_gates(
        sample,
        x_channel=x_channel,
        y_channel=y_channel,
        id_prefix=f"ai_{uuid4().hex[:6]}",
        labeler=label_clusters_with_gemini,
    )
    session.gates.extend(result.gates)
    stats = _stats_for_sample(session, sample.sample_id, compensation_enabled)
    columns = _columns_from_rows(stats, ["gate_name", "parent_gate", "channel_labels", "channels", "event_count", "percent_total", "percent_parent"])
    options = _gate_options(session.gates)
    selected = result.gates[0].gate_id if result.gates else (options[0]["value"] if options else None)
    status = _auto_gate_status(result.gates, result.warnings)
    return status, (
        gate_to_table(session.gates),
        stats,
        table_columns(columns),
        status,
        options,
        selected,
        _gate_stack_cards(session.gates, stats),
    )
