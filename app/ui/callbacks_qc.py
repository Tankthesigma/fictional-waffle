from __future__ import annotations

from dash import Input, Output, html

from app.core.session_store import WorkbenchSession


def register_qc_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("qc-table", "data"),
        Output("qc-cards", "children"),
        Output("qc-summary-cards", "children"),
        Output("qc-review-lanes", "children"),
        Input("sample-ids-store", "data"),
        Input("selected-sample-store", "data"),
    )
    def update_qc(_sample_ids, selected_sample):
        flags = session.all_qc_flags()
        selected_flags = session.qc_flags.get(selected_sample, []) if selected_sample else flags
        cards = [_qc_card("Severe", sum(1 for flag in flags if flag.severity == "severe"), "severe"), _qc_card("Warnings", sum(1 for flag in flags if flag.severity == "warning"), "warning"), _qc_card("Info", sum(1 for flag in flags if flag.severity == "info"), "info")]
        selected_cards = [_small_flag(flag) for flag in selected_flags[:6]] or [html.Div("No selected-sample QC flags.", className="flag-card")]
        return [flag.to_dict() for flag in flags], selected_cards, cards, _review_lanes(flags, selected_sample)


def _qc_card(label: str, count: int, tone: str):
    return html.Div([html.Span(label), html.Strong(str(count))], className=f"metric {tone}")


def _small_flag(flag):
    return html.Div([html.Strong(flag.title), html.P(flag.suggested_check)], className=f"flag-card {flag.severity}")


def _review_lanes(flags, selected_sample: str | None = None):
    scoped = [flag for flag in flags if not selected_sample or flag.sample_id == selected_sample]
    if not scoped:
        label = "selected sample" if selected_sample else "batch"
        return html.Div(f"No QC review flags for the {label}.", className="qc-lane empty")
    lanes = []
    for severity in ["severe", "warning", "info"]:
        severity_flags = [flag for flag in scoped if flag.severity == severity]
        if not severity_flags:
            continue
        lanes.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(severity),
                            html.Strong(f"{len(severity_flags)} review item(s)"),
                        ],
                        className="qc-lane-head",
                    ),
                    html.Div([_review_item(flag) for flag in severity_flags[:8]], className="qc-review-items"),
                ],
                className=f"qc-lane {severity}",
            )
        )
    return lanes


def _review_item(flag):
    metric = f"metric: {flag.metric_value} | threshold: {flag.threshold}"
    affected = ", ".join(flag.affects)
    channel = f" | channel: {flag.channel}" if flag.channel else ""
    return html.Div(
        [
            html.Div(
                [
                    html.Strong(flag.title),
                    html.Span(flag.code),
                ],
                className="qc-review-title",
            ),
            html.P(flag.explanation),
            html.Small(f"{metric}{channel} | affects: {affected}"),
            html.Em(flag.suggested_check),
        ],
        className="qc-review-item",
    )
