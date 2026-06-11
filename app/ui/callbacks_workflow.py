from __future__ import annotations

from dash import Input, Output, html

from app.core.session_store import WorkbenchSession


def register_workflow_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("analysis-guide", "children"),
        Input("sample-ids-store", "data"),
        Input("selected-sample-store", "data"),
        Input("gate-table", "data"),
        Input("comparison-table", "data"),
    )
    def update_analysis_guide(_sample_ids, selected_sample, _gate_rows, comparison_rows):
        return _analysis_guide(
            sample_count=len(session.samples),
            selected_sample=selected_sample,
            gate_count=len(session.gates),
            accepted_gate_count=sum(1 for gate in session.gates if gate.enabled and not gate.candidate),
            candidate_gate_count=sum(1 for gate in session.gates if gate.candidate),
            qc_flag_count=len(session.all_qc_flags()),
            comparison_count=len(comparison_rows or session.comparison_rows or []),
        )


def _analysis_guide(
    *,
    sample_count: int,
    selected_sample: str | None,
    gate_count: int,
    accepted_gate_count: int,
    candidate_gate_count: int,
    qc_flag_count: int,
    comparison_count: int,
):
    steps = [
        _step("Import", _state(sample_count > 0), f"{sample_count} sample(s) loaded" if sample_count else "Upload exported FCS or event-level CSV files."),
        _step(
            "Inspect",
            _state(bool(selected_sample), review=qc_flag_count > 0),
            f"{qc_flag_count} QC review flag(s)" if qc_flag_count else "Select a sample and verify inferred channels.",
        ),
        _step(
            "Gate",
            _gate_state(accepted_gate_count, candidate_gate_count, gate_count),
            _gate_detail(accepted_gate_count, candidate_gate_count, gate_count),
        ),
        _step(
            "Compare",
            _state(comparison_count > 0, waiting=sample_count < 2),
            f"{comparison_count} exploratory comparison row(s)" if comparison_count else "Add conditions, then choose control and treated groups.",
        ),
        _step(
            "Report",
            _state(sample_count > 0 and (accepted_gate_count > 0 or comparison_count > 0), waiting=sample_count == 0),
            "Ready for local PDF/PPTX export when review selections look right.",
        ),
    ]
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Guided analysis"),
                    html.Strong("Next-step checklist"),
                ],
                className="analysis-guide-head",
            ),
            html.Div(steps, className="analysis-guide-steps"),
        ],
        className="analysis-guide-panel",
    )


def _step(label: str, state: str, detail: str):
    return html.Div(
        [
            html.Span(state, className="analysis-step-state"),
            html.Strong(label),
            html.Small(detail),
        ],
        className=f"analysis-step {state}",
    )


def _state(done: bool, *, review: bool = False, waiting: bool = False) -> str:
    if waiting:
        return "waiting"
    if review:
        return "review"
    return "done" if done else "next"


def _gate_state(accepted_gate_count: int, candidate_gate_count: int, gate_count: int) -> str:
    if accepted_gate_count:
        return "done"
    if candidate_gate_count:
        return "review"
    if gate_count:
        return "review"
    return "next"


def _gate_detail(accepted_gate_count: int, candidate_gate_count: int, gate_count: int) -> str:
    if accepted_gate_count:
        return f"{accepted_gate_count} active accepted gate(s)"
    if candidate_gate_count:
        return f"{candidate_gate_count} candidate gate(s) need accept/edit/reject"
    if gate_count:
        return f"{gate_count} gate(s) need review before use"
    return "Create a rectangle/range gate or request candidate gates."
