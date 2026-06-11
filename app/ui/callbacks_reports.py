from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dash import Input, Output, State

from app.core.paths import EXPORT_ROOT
from app.core.session_store import WorkbenchSession


@dataclass(slots=True)
class FigureExportResult:
    paths: list[Path]
    warnings: list[str]


def register_report_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("report-status", "children"),
        Input("export-pdf", "n_clicks"),
        Input("export-pptx", "n_clicks"),
        State("selected-sample-store", "data"),
        State("compensation-enabled", "value"),
        State("x-channel", "value"),
        State("y-channel", "value"),
        State("hist-channel", "value"),
        State("plot-mode", "value"),
        State("transform", "value"),
        State("cofactor", "value"),
        State("max-events", "value"),
        prevent_initial_call=True,
    )
    def export_reports(
        pdf_clicks,
        pptx_clicks,
        selected_sample,
        compensation_enabled,
        x_channel,
        y_channel,
        hist_channel,
        plot_mode,
        transform,
        cofactor,
        max_events,
    ):
        from dash import callback_context
        from app.core.report_pdf import export_pdf_report
        from app.core.report_pptx import export_pptx_report

        action = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        sample = session.selected_sample(selected_sample)
        samples = session.sample_list()
        gate_stats = []
        if sample:
            from app.core.compensation import event_view
            from app.core.gating import apply_gate_tree
            from app.core.stats import gate_statistics

            use_compensation = isinstance(compensation_enabled, list) and "on" in compensation_enabled
            events = event_view(sample, use_compensation)
            current_view = "metadata_compensated" if use_compensation and sample.compensated_events is not None else "raw"
            compatible_gates = [gate for gate in session.gates if gate.metadata.get("event_view", "raw") == current_view]
            gate_stats = gate_statistics(events, compatible_gates, apply_gate_tree(events, compatible_gates), sample.fluorescence_channels)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        figure_export = _export_report_figures(
            stamp,
            sample,
            session.sample_list(),
            x_channel,
            y_channel,
            hist_channel,
            plot_mode,
            transform or "raw",
            cofactor or 150,
            max_events or 50_000,
            session.gates,
            isinstance(compensation_enabled, list) and "on" in compensation_enabled,
        )
        if action == "export-pdf":
            path = export_pdf_report(
                samples,
                session.all_qc_flags(),
                session.gates,
                gate_stats,
                EXPORT_ROOT / f"ask-flow-report-{stamp}.pdf",
                figure_paths=figure_export.paths,
                comparison_rows=session.comparison_rows,
            )
            return _report_status("PDF", path, figure_export)
        if action == "export-pptx":
            path = export_pptx_report(
                samples,
                session.all_qc_flags(),
                session.gates,
                gate_stats,
                EXPORT_ROOT / f"ask-flow-report-{stamp}.pptx",
                figure_paths=figure_export.paths,
                comparison_rows=session.comparison_rows,
            )
            return _report_status("PowerPoint", path, figure_export)
        return ""


def _export_report_figures(
    stamp: str,
    sample,
    samples,
    x_channel,
    y_channel,
    hist_channel,
    plot_mode,
    transform,
    cofactor,
    max_events,
    gates,
    use_compensation: bool,
) -> FigureExportResult:
    from app.core.plotting import histogram_figure, scatter_figure

    if sample is None:
        return FigureExportResult([], ["No selected sample was available for representative plot export."])
    asset_dir = EXPORT_ROOT / f"report-assets-{stamp}"
    asset_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    export_warnings: list[str] = []
    figures = [
        (
            "fsc-ssc.png",
            scatter_figure(
                sample,
                x_channel,
                y_channel,
                plot_mode=plot_mode or "scatter",
                transform=transform,
                cofactor=cofactor,
                max_events=max_events,
                gates=gates,
                use_compensation=use_compensation,
            ),
        ),
        (
            "histogram.png",
            histogram_figure(
                samples,
                hist_channel,
                transform=transform,
                cofactor=cofactor,
                max_events=max_events,
                use_compensation=use_compensation,
            ),
        ),
    ]
    for filename, figure in figures:
        path = asset_dir / filename
        try:
            figure.write_image(path, width=1200, height=760, scale=2)
        except Exception as exc:
            export_warnings.append(f"{filename}: {type(exc).__name__}: {exc}")
            continue
        paths.append(path)
    return FigureExportResult(paths, export_warnings)


def _report_status(report_type: str, path: Path, figure_export: FigureExportResult) -> str:
    if figure_export.warnings:
        reason = " | ".join(figure_export.warnings[:2])
        return f"{report_type} report exported to {path}. Static plot export needs review: {reason}"
    if not figure_export.paths:
        return f"{report_type} report exported to {path}. No static plot images were included."
    return f"{report_type} report exported to {path} with {len(figure_export.paths)} static plot image(s)."
