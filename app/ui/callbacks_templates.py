from __future__ import annotations

import logging
from dash import Input, Output, State, no_update

from app.core.paths import TEMPLATE_PATH
from app.core.session_store import WorkbenchSession
from app.ui.components import table_columns
from app.ui.callbacks_gating import _columns_from_rows, _gate_options, _gate_stack_cards

logger = logging.getLogger(__name__)


def register_template_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("template-status", "children"),
        Output("x-channel", "value", allow_duplicate=True),
        Output("y-channel", "value", allow_duplicate=True),
        Output("hist-channel", "value", allow_duplicate=True),
        Output("plot-mode", "value", allow_duplicate=True),
        Output("transform", "value", allow_duplicate=True),
        Output("cofactor", "value", allow_duplicate=True),
        Output("max-events", "value", allow_duplicate=True),
        Output("compensation-enabled", "value", allow_duplicate=True),
        Output("control-group", "value", allow_duplicate=True),
        Output("treated-group", "value", allow_duplicate=True),
        Output("gate-table", "data", allow_duplicate=True),
        Output("gate-stats-table", "data", allow_duplicate=True),
        Output("gate-stats-table", "columns", allow_duplicate=True),
        Output("manage-gate-id", "options", allow_duplicate=True),
        Output("manage-gate-id", "value", allow_duplicate=True),
        Output("gate-stack-cards", "children", allow_duplicate=True),
        Output("analysis-revision-store", "data", allow_duplicate=True),
        Input("save-analysis-template", "n_clicks"),
        Input("load-analysis-template", "n_clicks"),
        State("selected-sample-store", "data"),
        State("x-channel", "value"),
        State("y-channel", "value"),
        State("hist-channel", "value"),
        State("plot-mode", "value"),
        State("transform", "value"),
        State("cofactor", "value"),
        State("max-events", "value"),
        State("compensation-enabled", "value"),
        State("control-group", "value"),
        State("treated-group", "value"),
        State("analysis-revision-store", "data"),
        prevent_initial_call=True,
    )
    def template_actions(
        _save_clicks,
        _load_clicks,
        sample_id,
        x_channel,
        y_channel,
        hist_channel,
        plot_mode,
        transform,
        cofactor,
        max_events,
        compensation_enabled,
        control_group,
        treated_group,
        revision,
    ):
        from dash import callback_context
        from app.core.analysis_templates import (
            apply_template_channel_annotations,
            build_analysis_template,
            gates_from_template,
            load_analysis_template,
            save_analysis_template,
        )

        action = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        if action == "save-analysis-template":
            template = build_analysis_template(
                session.sample_list(),
                session.gates,
                plot_settings={
                    "x_channel": x_channel,
                    "y_channel": y_channel,
                    "hist_channel": hist_channel,
                    "plot_mode": plot_mode,
                    "transform": transform,
                    "cofactor": cofactor,
                    "max_events": max_events,
                    "compensation_enabled": compensation_enabled or [],
                },
                comparison_settings={
                    "control_group": control_group,
                    "treated_group": treated_group,
                },
                report_selections={"selected_sample": sample_id},
            )
            path = save_analysis_template(template, TEMPLATE_PATH)
            return _unchanged(
                f"Saved reusable analysis template to {path}. Raw event matrices and file paths are not embedded.",
                revision,
            )

        if action == "load-analysis-template":
            if not TEMPLATE_PATH.exists():
                return _unchanged(f"No saved analysis template found at {TEMPLATE_PATH}.", revision)
            try:
                template = load_analysis_template(TEMPLATE_PATH)
                session.gates = gates_from_template(template)
                applied = apply_template_channel_annotations(session.sample_list(), template)
            except Exception as exc:
                logger.exception("Analysis template could not be loaded from %s", TEMPLATE_PATH)
                return _unchanged(f"Analysis template could not be loaded: {exc}", revision)

            from app.core.gating import gate_to_table

            settings = template.plot_settings
            comparison = template.comparison_settings
            stats = _template_gate_stats(
                session,
                sample_id,
                settings.get("compensation_enabled", compensation_enabled),
            )
            stats_columns = _columns_from_rows(
                stats,
                ["gate_name", "parent_gate", "channel_labels", "channels", "event_count", "percent_total", "percent_parent"],
            )
            options = _gate_options(session.gates)
            selected_gate = options[0]["value"] if options else None
            next_revision = int(revision or 0) + 1
            return (
                f"Loaded analysis template from {TEMPLATE_PATH}. Restored {len(session.gates)} gate(s) and reapplied {applied} channel annotation(s).",
                settings.get("x_channel") or no_update,
                settings.get("y_channel") or no_update,
                settings.get("hist_channel") or no_update,
                settings.get("plot_mode") or no_update,
                settings.get("transform") or no_update,
                settings.get("cofactor") if settings.get("cofactor") is not None else no_update,
                settings.get("max_events") if settings.get("max_events") is not None else no_update,
                settings.get("compensation_enabled") if isinstance(settings.get("compensation_enabled"), list) else no_update,
                comparison.get("control_group") or no_update,
                comparison.get("treated_group") or no_update,
                gate_to_table(session.gates),
                stats,
                table_columns(stats_columns),
                options,
                selected_gate,
                _gate_stack_cards(session.gates, stats),
                next_revision,
            )

        return _unchanged("", revision)


def _unchanged(status: str, revision) -> tuple[object, ...]:
    return (
        status,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        no_update,
        int(revision or 0),
    )


def _template_gate_stats(session: WorkbenchSession, sample_id: str | None, compensation_enabled) -> list[dict[str, object]]:
    sample = session.selected_sample(sample_id)
    if sample is None:
        return []
    from app.core.channel_labels import channel_label_map
    from app.core.compensation import event_view
    from app.core.gating import apply_gate_tree
    from app.core.stats import gate_statistics

    use_compensation = isinstance(compensation_enabled, list) and "on" in compensation_enabled and sample.compensated_events is not None
    view_name = "metadata_compensated" if use_compensation else "raw"
    compatible_gates = [gate for gate in session.gates if gate.metadata.get("event_view", "raw") == view_name]
    events = event_view(sample, use_compensation)
    masks = apply_gate_tree(events, compatible_gates)
    return gate_statistics(events, compatible_gates, masks, sample.fluorescence_channels, channel_label_map([sample]))
