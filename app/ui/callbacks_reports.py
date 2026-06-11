from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dash import Input, Output, State, html

from app.core.paths import EXPORT_ROOT
from app.core.session_store import WorkbenchSession


@dataclass(slots=True)
class FigureExportResult:
    paths: list[Path]
    warnings: list[str]


def register_report_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("report-readiness", "children"),
        Output("report-outline-preview", "children"),
        Input("sample-ids-store", "data"),
        Input("selected-sample-store", "data"),
        Input("gate-table", "data"),
        Input("comparison-table", "data"),
        Input("qc-table", "data"),
        Input("x-channel", "value"),
        Input("y-channel", "value"),
        Input("hist-channel", "value"),
    )
    def update_report_readiness(_sample_ids, selected_sample, _gate_rows, comparison_rows, _qc_rows, x_channel, y_channel, hist_channel):
        from app.core.report_outline import report_outline

        sample = session.selected_sample(selected_sample)
        samples = session.sample_list()
        return (
            _report_readiness_cards(
                sample_count=len(session.samples),
                selected_sample_id=sample.sample_id if sample else None,
                channel_count=sum(item.channel_count for item in samples),
                qc_count=len(session.all_qc_flags()),
                gate_count=len(session.gates),
                comparison_count=len(comparison_rows or session.comparison_rows or []),
                has_scatter=bool(sample and x_channel and y_channel),
                has_histogram=bool(sample and hist_channel),
            ),
            _report_outline_cards(
                report_outline(
                    samples,
                    session.all_qc_flags(),
                    session.gates,
                    comparison_rows=comparison_rows or session.comparison_rows or [],
                )
            ),
        )

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
            from app.core.channel_labels import channel_label_map
            from app.core.compensation import event_view
            from app.core.gating import apply_gate_tree
            from app.core.stats import gate_statistics

            use_compensation = isinstance(compensation_enabled, list) and "on" in compensation_enabled
            events = event_view(sample, use_compensation)
            current_view = "metadata_compensated" if use_compensation and sample.compensated_events is not None else "raw"
            compatible_gates = [gate for gate in session.gates if gate.metadata.get("event_view", "raw") == current_view]
            gate_stats = gate_statistics(
                events,
                compatible_gates,
                apply_gate_tree(events, compatible_gates),
                sample.fluorescence_channels,
                channel_label_map([sample]),
            )
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


def _report_readiness_cards(
    *,
    sample_count: int,
    selected_sample_id: str | None,
    channel_count: int,
    qc_count: int,
    gate_count: int,
    comparison_count: int,
    has_scatter: bool,
    has_histogram: bool,
):
    sections = [
        ("Samples", "ready" if sample_count else "waiting", f"{sample_count} uploaded sample(s)"),
        ("Channels", "ready" if channel_count else "waiting", f"{channel_count} channel summary row(s)"),
        ("QC", "review" if qc_count else ("ready" if sample_count else "waiting"), f"{qc_count} review flag(s)"),
        ("Representative plots", "ready" if has_scatter or has_histogram else "waiting", _plot_detail(selected_sample_id, has_scatter, has_histogram)),
        ("Gate statistics", "ready" if gate_count else "review", f"{gate_count} gate definition(s)"),
        ("Comparison", "ready" if comparison_count else "review", f"{comparison_count} exploratory comparison row(s)"),
        ("Safety note", "ready", "post-acquisition aid; no instrument control"),
    ]
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Report contents"),
                    html.Strong("Export readiness"),
                ],
                className="report-readiness-head",
            ),
            html.Div([_readiness_item(label, state, detail) for label, state, detail in sections], className="report-readiness-grid"),
        ],
        className="report-readiness-panel",
    )


def _readiness_item(label: str, state: str, detail: str):
    return html.Div(
        [
            html.Span(state, className="report-readiness-state"),
            html.Strong(label),
            html.Small(detail),
        ],
        className=f"report-readiness-item {state}",
    )


def _plot_detail(selected_sample_id: str | None, has_scatter: bool, has_histogram: bool) -> str:
    if has_scatter and has_histogram:
        return f"{selected_sample_id}: scatter and histogram selected"
    if has_scatter:
        return f"{selected_sample_id}: scatter selected"
    if has_histogram:
        return f"{selected_sample_id}: histogram selected"
    return "select a sample and plot channels for static figures"


def _report_outline_cards(rows: list[dict[str, str]]):
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Report narrative"),
                    html.Strong("Review outline"),
                ],
                className="report-outline-head",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(row["status"], className="report-outline-state"),
                            html.Strong(row["section"]),
                            html.P(row["note"]),
                            html.Small(row["detail"]),
                        ],
                        className=f"report-outline-item {row['status']}",
                    )
                    for row in rows
                ],
                className="report-outline-grid",
            ),
        ],
        className="report-outline-panel",
    )
