from __future__ import annotations

from datetime import datetime
from pathlib import Path

from dash import Input, Output, State

from app.core.compensation import event_view
from app.core.gating import apply_gate_tree
from app.core.report_pdf import export_pdf_report
from app.core.report_pptx import export_pptx_report
from app.core.session_store import WorkbenchSession
from app.core.stats import gate_statistics

EXPORT_ROOT = Path("exports")


def register_report_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("report-status", "children"),
        Input("export-pdf", "n_clicks"),
        Input("export-pptx", "n_clicks"),
        State("selected-sample-store", "data"),
        State("compensation-enabled", "value"),
        prevent_initial_call=True,
    )
    def export_reports(pdf_clicks, pptx_clicks, selected_sample, compensation_enabled):
        from dash import callback_context

        action = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        sample = session.selected_sample(selected_sample)
        samples = session.sample_list()
        gate_stats = []
        if sample:
            use_compensation = isinstance(compensation_enabled, list) and "on" in compensation_enabled
            events = event_view(sample, use_compensation)
            current_view = "metadata_compensated" if use_compensation and sample.compensated_events is not None else "raw"
            compatible_gates = [gate for gate in session.gates if gate.metadata.get("event_view", "raw") == current_view]
            gate_stats = gate_statistics(events, compatible_gates, apply_gate_tree(events, compatible_gates), sample.fluorescence_channels)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if action == "export-pdf":
            path = export_pdf_report(samples, session.all_qc_flags(), session.gates, gate_stats, EXPORT_ROOT / f"ask-flow-report-{stamp}.pdf")
            return f"PDF report exported to {path}."
        if action == "export-pptx":
            path = export_pptx_report(samples, session.all_qc_flags(), session.gates, gate_stats, EXPORT_ROOT / f"ask-flow-report-{stamp}.pptx")
            return f"PowerPoint report exported to {path}."
        return ""
