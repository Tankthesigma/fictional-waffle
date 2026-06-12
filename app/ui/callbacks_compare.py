from __future__ import annotations

import csv
from io import StringIO

from dash import Input, Output, html

from app.core.paths import EXPORT_ROOT
from app.core.session_store import WorkbenchSession
from app.ui.components import table_columns


def register_compare_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("grouping-readiness-summary", "children"),
        Output("grouping-readiness-table", "data"),
        Input("sample-ids-store", "data"),
    )
    def update_grouping_readiness(_sample_ids):
        from app.core.grouping import grouping_readiness_rows, grouping_readiness_summary

        samples = session.sample_list()
        return _grouping_summary_cards(grouping_readiness_summary(samples)), grouping_readiness_rows(samples)

    @app.callback(
        Output("manifest-template-download", "data"),
        Input("download-manifest-template", "n_clicks"),
        prevent_initial_call=True,
    )
    def download_manifest_template(_clicks):
        from app.core.grouping import manifest_template_columns, manifest_template_rows

        output = StringIO()
        columns = manifest_template_columns()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(manifest_template_rows(session.sample_list()))
        return {
            "content": output.getvalue(),
            "filename": "ask-flow-manifest-template.csv",
            "type": "text/csv",
        }

    @app.callback(
        Output("control-group", "options"),
        Output("treated-group", "options"),
        Output("control-group", "value"),
        Output("treated-group", "value"),
        Input("sample-ids-store", "data"),
    )
    def update_group_options(_sample_ids):
        groups = _condition_groups(session.sample_list())
        options = [{"label": group, "value": group} for group in groups]
        control, treated = _default_groups(groups)
        return options, options, control, treated

    @app.callback(
        Output("batch-table", "data"),
        Output("median-table", "data"),
        Output("median-table", "columns"),
        Output("batch-gate-stats-table", "data"),
        Output("batch-gate-stats-table", "columns"),
        Output("population-frequency-table", "data"),
        Output("population-frequency-table", "columns"),
        Output("comparison-table", "data"),
        Output("compare-status", "children"),
        Output("compare-summary-cards", "children"),
        Output("compare-insights", "children"),
        Output("comparison-delta-chart", "figure"),
        Input("sample-ids-store", "data"),
        Input("compare-button", "n_clicks"),
        Input("batch-apply-gates", "n_clicks"),
        Input("export-comparison-csv", "n_clicks"),
        Input("export-population-frequency-csv", "n_clicks"),
        Input("compensation-enabled", "value"),
        Input("control-group", "value"),
        Input("treated-group", "value"),
        Input("gate-table", "data"),
    )
    def update_compare(
        _sample_ids,
        _compare_clicks,
        _batch_apply_clicks,
        _export_clicks,
        _export_frequency_clicks,
        compensation_enabled,
        control_group,
        treated_group,
        _gate_rows,
    ):
        from dash import callback_context
        from app.core.compare import (
            batch_gate_statistics_table,
            batch_table,
            compare_control_treated,
            comparison_insights,
            comparison_summary,
            fluorescence_median_table,
            population_frequency_table,
        )
        from app.core.export_tables import export_rows_csv
        from app.core.plotting import comparison_delta_chart

        action = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        samples = session.sample_list()
        use_compensation = isinstance(compensation_enabled, list) and "on" in compensation_enabled
        medians = fluorescence_median_table(samples, use_compensation=use_compensation)
        batch_gate_rows = batch_gate_statistics_table(samples, session.gates, use_compensation=use_compensation)
        population_frequency_rows = population_frequency_table(samples, session.gates, use_compensation=use_compensation)
        comparison_rows = []
        status = ""
        if control_group and treated_group:
            comparison_rows = [
                row.to_dict()
                for row in compare_control_treated(samples, control_group, treated_group, use_compensation=use_compensation)
            ]
            session.comparison_rows = comparison_rows
        if action == "export-comparison-csv":
            if comparison_rows:
                path = export_rows_csv(comparison_rows, EXPORT_ROOT / "comparison-results.csv")
                status = f"Exported comparison CSV to {path}."
            else:
                status = "Choose control and treated groups before exporting comparison results."
        elif action == "export-population-frequency-csv":
            if population_frequency_rows:
                path = export_rows_csv(population_frequency_rows, EXPORT_ROOT / "population-frequency-table.csv")
                status = f"Exported population frequency CSV to {path}."
            else:
                status = "No population frequencies available. Add gates, then apply them across the batch."
        elif action == "batch-apply-gates":
            status = (
                f"Applied {len(session.gates)} gate definition(s) across {len(samples)} sample(s); "
                f"{len(batch_gate_rows)} gate-stat row(s) and {len(population_frequency_rows)} population row(s) are shown."
            )
        median_columns = _columns_from_rows(medians, ["sample_id", "condition"])
        batch_gate_columns = _columns_from_rows(
            batch_gate_rows,
            ["sample_id", "condition", "replicate", "gate_name", "parent_gate", "event_count", "percent_total", "percent_parent", "gate_warning"],
        )
        frequency_columns = _columns_from_rows(population_frequency_rows, ["population", "parent_gate"])
        return (
            batch_table(samples),
            medians,
            table_columns(median_columns),
            batch_gate_rows,
            table_columns(batch_gate_columns),
            population_frequency_rows,
            table_columns(frequency_columns),
            comparison_rows,
            status,
            _summary_cards(comparison_summary(comparison_rows)),
            _insight_cards(comparison_insights(comparison_rows, control_group, treated_group)),
            comparison_delta_chart(comparison_rows),
        )


def _columns_from_rows(rows: list[dict[str, object]], preferred: list[str]) -> list[str]:
    seen = list(preferred)
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


def _summary_cards(rows: list[dict[str, object]]):
    if not rows:
        return []
    return [
        html.Div(
            [
                html.Span(str(row["label"])),
                html.Strong(str(row["value"])),
                html.Small(str(row["detail"])),
            ],
            className=f"metric compare-metric {row.get('tone', '')}".strip(),
        )
        for row in rows
    ]


def _insight_cards(rows: list[dict[str, str]]):
    return [
        html.Div(
            [
                html.Span(row["severity"]),
                html.Strong(row["title"]),
                html.P(row["message"]),
                html.Small(row["detail"]),
            ],
            className=f"compare-insight {row['severity']}",
        )
        for row in rows
    ]


def _grouping_summary_cards(summary: dict[str, int | str]):
    return html.Div(
        [
            _grouping_metric("Status", str(summary["status"]), f"{summary['group_count']} condition group(s)"),
            _grouping_metric("Samples", str(summary["sample_count"]), f"{summary['labeled_samples']} labeled"),
            _grouping_metric("Needs Labels", str(summary["unlabeled_samples"]), "condition required for Compare"),
            _grouping_metric("Control/Treated", f"{summary['control_like']} / {summary['treated_like']}", "detected from condition/control_type"),
        ],
        className="grouping-readiness-metrics",
    )


def _grouping_metric(label: str, value: str, detail: str):
    return html.Div([html.Span(label), html.Strong(value), html.Small(detail)], className="grouping-readiness-metric")


def _condition_groups(samples) -> list[str]:
    groups = sorted({str(sample.condition).strip() for sample in samples if sample.condition and str(sample.condition).strip()})
    return groups


def _default_groups(groups: list[str]) -> tuple[str | None, str | None]:
    if not groups:
        return None, None
    control = _first_matching(groups, ("control", "untreated", "vehicle", "unstained", "baseline")) or groups[0]
    treated = _first_matching(groups, ("treated", "stimulated", "drug", "test", "experimental"))
    if treated is None:
        treated = next((group for group in groups if group != control), None)
    return control, treated


def _first_matching(groups: list[str], tokens: tuple[str, ...]) -> str | None:
    for group in groups:
        normalized = group.lower()
        if any(token in normalized for token in tokens):
            return group
    return None
