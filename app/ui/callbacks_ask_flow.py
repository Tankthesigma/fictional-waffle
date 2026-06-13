from __future__ import annotations

from datetime import datetime
import re

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
        Output("ask-flow-command-history-store", "data"),
        Output("global-assistant-timeline", "children"),
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
        State("ask-flow-command-history-store", "data"),
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
        history,
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
        elif _requests_candidate_gates(question or ""):
            candidate_status, auto_gate_outputs = _run_candidate_gates_from_chat(session, sample, compensation_enabled)
            plan.messages.append(candidate_status)
        elif _requests_scatter_review_gate(question or ""):
            scatter_status, auto_gate_outputs = _run_scatter_gate_from_chat(session, sample, compensation_enabled)
            plan.messages.append(scatter_status)
        elif _requests_histogram_gate(question or ""):
            histogram_status, auto_gate_outputs = _run_histogram_gate_from_chat(session, sample, plan.updates.get("hist_channel"), compensation_enabled)
            plan.messages.append(histogram_status)
        elif _requests_current_view_gate(question or ""):
            view_status, auto_gate_outputs = _run_current_view_gate_from_chat(
                session,
                sample,
                plan.updates.get("x_channel", x_channel),
                plan.updates.get("y_channel", y_channel),
                compensation_enabled,
            )
            plan.messages.append(view_status)
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
        next_history = _append_history(history, question or "", plan.messages, gemini.status, triggered)
        return (
            answer_panel,
            answer_panel,
            next_history,
            _history_cards(next_history),
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


def _append_history(history, question: str, action_messages: list[str], status: str, triggered: str) -> list[dict[str, object]]:
    rows = history if isinstance(history, list) else []
    label = _trigger_label(triggered)
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "label": label,
        "question": question.strip() or label,
        "actions": list(action_messages),
        "status": status,
    }
    return [entry, *[row for row in rows if isinstance(row, dict)]][:5]


def _trigger_label(triggered: str) -> str:
    return {
        "ask-flow-button": "Ask Flow",
        "global-assistant-button": "Command",
        "global-quick-qc": "Quick QC",
        "global-quick-singlets": "Quick Singlets",
        "global-quick-cluster-gates": "Quick Cluster Gates",
        "global-quick-report": "Quick Report",
    }.get(triggered, "Command")


def _history_cards(history) -> list:
    rows = history if isinstance(history, list) else []
    if not rows:
        return []
    cards = [html.Div([html.Span("Recent"), html.Strong("Copilot timeline")], className="assistant-timeline-header")]
    for row in rows[:5]:
        actions = row.get("actions") if isinstance(row.get("actions"), list) else []
        cards.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(str(row.get("time") or ""), className="assistant-timeline-time"),
                            html.Strong(str(row.get("label") or "Command")),
                        ],
                        className="assistant-timeline-topline",
                    ),
                    html.P(str(row.get("question") or "Command")),
                    html.Ul([html.Li(str(action)) for action in actions[:4]]) if actions else html.Small("No workbench action was needed."),
                ],
                className="assistant-timeline-card",
            )
        )
    return cards


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
    if any(phrase in normalized for phrase in ("auto gate", "autogate", "cluster gate", "ai gate", "suggest gates from clusters", "cluster-guided gate")):
        return True
    return bool(re.search(r"\b(?:make|create|build|run|do|suggest|review)\b.*\bclust\w*", normalized))


def _requests_singlet_gate(question: str) -> bool:
    normalized = question.lower()
    return "singlet" in normalized and any(phrase in normalized for phrase in ("gate", "preset", "create", "make", "add", "suggest"))


def _requests_candidate_gates(question: str) -> bool:
    normalized = question.lower()
    return any(phrase in normalized for phrase in ("suggest candidate gates", "candidate gates", "suggest review gates", "suggest gates", "review-needed gates"))


def _requests_scatter_review_gate(question: str) -> bool:
    normalized = question.lower()
    scatter_words = ("fsc", "ssc", "scatter", "main population", "cleanup gate", "debris gate")
    gate_words = ("gate", "gating", "population")
    return any(word in normalized for word in scatter_words) and any(word in normalized for word in gate_words)


def _requests_histogram_gate(question: str) -> bool:
    normalized = question.lower()
    return any(word in normalized for word in ("histogram gate", "hist gate", "range gate", "positive gate", "marker gate"))


def _requests_current_view_gate(question: str) -> bool:
    normalized = question.lower()
    gate_words = ("gate", "gating", "population", "region")
    action_words = ("make", "create", "build", "add", "gate this", "gate current", "current view", "this plot", "this graph")
    return any(word in normalized for word in gate_words) and any(word in normalized for word in action_words)


def _empty_gate_outputs():
    return (no_update, no_update, no_update, no_update, no_update, no_update, no_update)


def _gate_outputs(session: WorkbenchSession, sample, selected_gate_id: str | None, compensation_enabled, status: str):
    from app.core.gating import gate_to_table
    from app.ui.callbacks_gating import _columns_from_rows, _gate_options, _gate_stack_cards, _stats_for_sample
    from app.ui.components import table_columns

    stats = _stats_for_sample(session, sample.sample_id, compensation_enabled) if sample is not None else []
    columns = _columns_from_rows(stats, ["gate_name", "parent_gate", "channel_labels", "channels", "event_count", "percent_total", "percent_parent"])
    options = _gate_options(session.gates)
    selected = selected_gate_id or (options[0]["value"] if options else None)
    return (
        gate_to_table(session.gates),
        stats,
        table_columns(columns),
        status,
        options,
        selected,
        _gate_stack_cards(session.gates, stats),
    )


def _compensated_view_name(sample, use_compensation: bool) -> str:
    return "metadata_compensated" if use_compensation and sample is not None and sample.compensated_events is not None else "raw"


def _use_compensation(sample, compensation_enabled) -> bool:
    return bool(compensation_enabled and "on" in compensation_enabled and sample is not None and sample.compensated_events is not None)


def _run_current_view_gate_from_chat(session: WorkbenchSession, sample, x_channel, y_channel, compensation_enabled):
    from uuid import uuid4

    from app.core.compensation import event_view
    from app.core.gating import review_current_view_gate

    if sample is None:
        return "Current-view gate skipped: select a sample first.", _empty_gate_outputs()
    use_compensation = _use_compensation(sample, compensation_enabled)
    gate = review_current_view_gate(event_view(sample, use_compensation), x_channel, y_channel, uuid4().hex[:8], name="Ask Flow current-view gate")
    if gate is None:
        return "Current-view gate skipped: choose two numeric plot channels first.", _empty_gate_outputs()
    gate.metadata["event_view"] = _compensated_view_name(sample, use_compensation)
    gate.metadata["ask_flow_action"] = "current_view_gate"
    session.gates.append(gate)
    status = f"Added editable review-needed current-view gate: {gate.name}. Review/edit before using final statistics."
    return status, _gate_outputs(session, sample, gate.gate_id, compensation_enabled, status)


def _run_scatter_gate_from_chat(session: WorkbenchSession, sample, compensation_enabled):
    from uuid import uuid4

    from app.core.compensation import event_view
    from app.core.gating import review_scatter_gate

    if sample is None:
        return "FSC/SSC gate skipped: select a sample first.", _empty_gate_outputs()
    use_compensation = _use_compensation(sample, compensation_enabled)
    gate = review_scatter_gate(event_view(sample, use_compensation), sample.channels, uuid4().hex[:8], name="Ask Flow FSC/SSC gate")
    if gate is None:
        return "FSC/SSC gate skipped: FSC/SSC channels were not confidently identified.", _empty_gate_outputs()
    gate.metadata["event_view"] = _compensated_view_name(sample, use_compensation)
    gate.metadata["ask_flow_action"] = "scatter_review_gate"
    session.gates.append(gate)
    status = f"Added editable review-needed FSC/SSC gate: {gate.name}. Review/edit before using final statistics."
    return status, _gate_outputs(session, sample, gate.gate_id, compensation_enabled, status)


def _run_candidate_gates_from_chat(session: WorkbenchSession, sample, compensation_enabled):
    from app.core.compensation import event_view
    from app.core.gating import suggest_candidate_gates

    if sample is None:
        return "Candidate gate suggestion skipped: select a sample first.", _empty_gate_outputs()
    use_compensation = _use_compensation(sample, compensation_enabled)
    current_view = _compensated_view_name(sample, use_compensation)
    existing_ids = {gate.gate_id for gate in session.gates}
    suggestions = [
        gate
        for gate in suggest_candidate_gates(event_view(sample, use_compensation), sample.channels, id_prefix=sample.sample_id)
        if gate.gate_id not in existing_ids
    ]
    for gate in suggestions:
        gate.metadata["event_view"] = current_view
        gate.metadata["ask_flow_action"] = "candidate_gate_suggestion"
    session.gates.extend(suggestions)
    status = (
        f"Added {len(suggestions)} disabled candidate gate(s) for review. Accept, edit, or reject before final statistics."
        if suggestions
        else "No new stable candidate gates were suggested for this sample."
    )
    selected = suggestions[0].gate_id if suggestions else None
    return status, _gate_outputs(session, sample, selected, compensation_enabled, status)


def _run_histogram_gate_from_chat(session: WorkbenchSession, sample, requested_channel, compensation_enabled):
    from uuid import uuid4

    import numpy as np
    import pandas as pd

    from app.core.compensation import event_view
    from app.core.gating import histogram_range_gate

    if sample is None:
        return "Histogram gate skipped: select a sample first.", _empty_gate_outputs()
    use_compensation = _use_compensation(sample, compensation_enabled)
    events = event_view(sample, use_compensation)
    channel = requested_channel or _first_fluorescence_channel(sample)
    if not channel or channel not in events:
        return "Histogram gate skipped: choose a histogram or fluorescence channel first.", _empty_gate_outputs()
    values = pd.to_numeric(events[channel], errors="coerce").to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size < 10:
        return "Histogram gate skipped: not enough finite events on the selected channel.", _empty_gate_outputs()
    low, high = np.nanpercentile(finite, [5, 95])
    if not np.isfinite(low) or not np.isfinite(high) or low == high:
        return "Histogram gate skipped: selected channel does not have a usable numeric range.", _empty_gate_outputs()
    gate = histogram_range_gate(uuid4().hex[:8], f"Ask Flow {channel} range", channel, float(low), float(high))
    gate.review_status = "review_needed"
    gate.metadata["event_view"] = _compensated_view_name(sample, use_compensation)
    gate.metadata["ask_flow_action"] = "histogram_range_gate"
    gate.metadata["review_gate_reason"] = f"central 5-95% range on {channel}; review/edit before final statistics"
    session.gates.append(gate)
    status = f"Added editable review-needed histogram gate on {channel}. Review/edit before using final statistics."
    return status, _gate_outputs(session, sample, gate.gate_id, compensation_enabled, status)


def _first_fluorescence_channel(sample) -> str | None:
    for channel in sample.channels:
        if channel.role == "fluorescence":
            return channel.raw_name
    return sample.channels[0].raw_name if sample.channels else None


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
