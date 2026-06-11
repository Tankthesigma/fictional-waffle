from __future__ import annotations

from uuid import uuid4

from dash import Input, Output, State, no_update

from app.core.paths import EXPORT_ROOT, GATES_PATH, PROJECT_PATH
from app.core.session_store import WorkbenchSession
from app.ui.components import table_columns


def register_gating_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("gate-table", "data"),
        Output("gate-stats-table", "data"),
        Output("gate-stats-table", "columns"),
        Output("gate-status", "children"),
        Input("add-rectangle-gate", "n_clicks"),
        Input("add-histogram-gate", "n_clicks"),
        Input("save-gates", "n_clicks"),
        Input("load-gates", "n_clicks"),
        Input("save-project", "n_clicks"),
        Input("load-project", "n_clicks"),
        Input("export-gate-stats", "n_clicks"),
        State("selected-sample-store", "data"),
        State("x-channel", "value"),
        State("y-channel", "value"),
        State("hist-channel", "value"),
        State("plot-mode", "value"),
        State("transform", "value"),
        State("cofactor", "value"),
        State("max-events", "value"),
        State("control-group", "value"),
        State("treated-group", "value"),
        State("gate-name", "value"),
        State("gate-x-min", "value"),
        State("gate-x-max", "value"),
        State("gate-y-min", "value"),
        State("gate-y-max", "value"),
        State("hist-gate-name", "value"),
        State("hist-gate-min", "value"),
        State("hist-gate-max", "value"),
        State("compensation-enabled", "value"),
        prevent_initial_call=True,
    )
    def gate_actions(
        add_clicks,
        add_hist_clicks,
        save_clicks,
        load_clicks,
        save_project_clicks,
        load_project_clicks,
        export_clicks,
        sample_id,
        x_channel,
        y_channel,
        hist_channel,
        plot_mode,
        transform,
        cofactor,
        max_events,
        control_group,
        treated_group,
        gate_name,
        x_min,
        x_max,
        y_min,
        y_max,
        hist_gate_name,
        hist_min,
        hist_max,
        compensation_enabled,
    ):
        from dash import callback_context
        from app.core.gating import gate_to_table

        action = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        status = ""
        if action == "add-rectangle-gate":
            from app.core.gating import rectangle_gate

            if not all(value is not None for value in [x_channel, y_channel, x_min, x_max, y_min, y_max]):
                return no_update, no_update, no_update, "Choose x/y channels and complete all rectangle bounds."
            gate = rectangle_gate(
                uuid4().hex[:8],
                gate_name or "User rectangle gate",
                x_channel,
                y_channel,
                float(min(x_min, x_max)),
                float(max(x_min, x_max)),
                float(min(y_min, y_max)),
                float(max(y_min, y_max)),
            )
            sample = session.selected_sample(sample_id)
            use_compensation = _is_compensation_on(compensation_enabled) and sample is not None and sample.compensated_events is not None
            gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
            session.gates.append(gate)
            status = f"Added user-defined rectangle gate: {gate.name} ({gate.metadata['event_view']})."
        elif action == "add-histogram-gate":
            from app.core.gating import histogram_range_gate

            if not all(value is not None for value in [hist_channel, hist_min, hist_max]):
                return no_update, no_update, no_update, "Choose a histogram channel and complete range bounds."
            gate = histogram_range_gate(
                uuid4().hex[:8],
                hist_gate_name or "User histogram gate",
                hist_channel,
                float(min(hist_min, hist_max)),
                float(max(hist_min, hist_max)),
            )
            sample = session.selected_sample(sample_id)
            use_compensation = _is_compensation_on(compensation_enabled) and sample is not None and sample.compensated_events is not None
            gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
            session.gates.append(gate)
            status = f"Added user-defined histogram range gate: {gate.name} ({gate.metadata['event_view']})."
        elif action == "save-gates":
            from app.core.gating import save_gates

            save_gates(session.gates, GATES_PATH)
            status = f"Saved gates to {GATES_PATH}."
        elif action == "load-gates":
            from app.core.gating import load_gates

            if GATES_PATH.exists():
                try:
                    session.gates = load_gates(GATES_PATH)
                    status = f"Loaded gates from {GATES_PATH}."
                except Exception as exc:
                    status = f"Gate file could not be loaded: {exc}"
            else:
                status = f"No saved gate file found at {GATES_PATH}."
        elif action == "save-project":
            from app.core.project_store import build_project_state, save_project

            project = build_project_state(
                session.sample_list(),
                session.gates,
                session.all_qc_flags(),
                transform_settings={
                    "x_channel": x_channel,
                    "y_channel": y_channel,
                    "hist_channel": hist_channel,
                    "plot_mode": plot_mode,
                    "transform": transform,
                    "cofactor": cofactor,
                    "max_events": max_events,
                },
                comparison_settings={
                    "control_group": control_group,
                    "treated_group": treated_group,
                    "comparison_rows": session.comparison_rows,
                },
                report_selections={"selected_sample": sample_id},
            )
            path = save_project(project, PROJECT_PATH)
            status = f"Saved project JSON to {path}. Raw event matrices are not embedded."
        elif action == "load-project":
            from app.core.project_store import gates_from_project, load_project

            if PROJECT_PATH.exists():
                try:
                    project = load_project(PROJECT_PATH)
                    session.gates = gates_from_project(project)
                    session.comparison_rows = list(project.comparison_settings.get("comparison_rows", []))
                    status = (
                        f"Loaded project metadata from {PROJECT_PATH}. Restored {len(session.gates)} gate(s); "
                        "re-upload raw FCS/CSV files if samples are not already loaded."
                    )
                except Exception as exc:
                    status = f"Project file could not be loaded: {exc}"
            else:
                status = f"No saved project file found at {PROJECT_PATH}."
        sample = session.selected_sample(sample_id)
        stats = []
        if sample:
            from app.core.compensation import event_view
            from app.core.gating import apply_gate_tree
            from app.core.stats import gate_statistics

            events = event_view(sample, _is_compensation_on(compensation_enabled))
            compatible_gates = [
                gate
                for gate in session.gates
                if gate.metadata.get("event_view", "raw")
                == ("metadata_compensated" if _is_compensation_on(compensation_enabled) and sample.compensated_events is not None else "raw")
            ]
            masks = apply_gate_tree(events, compatible_gates)
            stats = gate_statistics(events, compatible_gates, masks, sample.fluorescence_channels)
        if action == "export-gate-stats":
            from app.core.export_tables import export_rows_csv

            if stats:
                path = export_rows_csv(stats, EXPORT_ROOT / "gate-statistics.csv")
                status = f"Exported gate statistics CSV to {path}."
            else:
                status = "No gate statistics available to export."
        stats_columns = _columns_from_rows(stats, ["gate_name", "parent_gate", "channels", "event_count", "percent_total", "percent_parent"])
        return gate_to_table(session.gates), stats, table_columns(stats_columns), status


def _columns_from_rows(rows: list[dict[str, object]], preferred: list[str]) -> list[str]:
    seen = list(preferred)
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


def _is_compensation_on(value) -> bool:
    return isinstance(value, list) and "on" in value
