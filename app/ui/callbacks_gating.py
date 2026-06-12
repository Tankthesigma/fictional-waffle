from __future__ import annotations

import logging
from uuid import uuid4

from dash import Input, Output, State, html, no_update

from app.core.paths import EXPORT_ROOT, GATES_PATH, PROJECT_PATH
from app.core.session_store import WorkbenchSession
from app.ui.components import table_columns

logger = logging.getLogger(__name__)


def register_gating_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("gate-table", "data"),
        Output("gate-stats-table", "data"),
        Output("gate-stats-table", "columns"),
        Output("gate-status", "children"),
        Output("manage-gate-id", "options"),
        Output("manage-gate-id", "value"),
        Output("gate-stack-cards", "children"),
        Input("add-rectangle-gate", "n_clicks"),
        Input("add-review-current-view-gate", "n_clicks"),
        Input("add-review-scatter-gate", "n_clicks"),
        Input("add-histogram-gate", "n_clicks"),
        Input("add-quadrant-gates", "n_clicks"),
        Input("add-ellipse-gate", "n_clicks"),
        Input("add-birange-gate", "n_clicks"),
        Input("suggest-candidate-gates", "n_clicks"),
        Input("ai-auto-gate-clusters", "n_clicks"),
        Input("accept-candidate-gates", "n_clicks"),
        Input("reject-candidate-gates", "n_clicks"),
        Input("rename-gate", "n_clicks"),
        Input("toggle-gate", "n_clicks"),
        Input("delete-gate", "n_clicks"),
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
        State("quadrant-gate-name", "value"),
        State("quadrant-x-threshold", "value"),
        State("quadrant-y-threshold", "value"),
        State("ellipse-gate-name", "value"),
        State("ellipse-center-x", "value"),
        State("ellipse-center-y", "value"),
        State("ellipse-radius-x", "value"),
        State("ellipse-radius-y", "value"),
        State("birange-gate-name", "value"),
        State("birange-x-min", "value"),
        State("birange-x-max", "value"),
        State("birange-y-min", "value"),
        State("birange-y-max", "value"),
        State("manage-gate-id", "value"),
        State("manage-gate-name", "value"),
        State("compensation-enabled", "value"),
        prevent_initial_call=True,
    )
    def gate_actions(
        add_clicks,
        add_review_current_view_clicks,
        add_review_scatter_clicks,
        add_hist_clicks,
        add_quadrant_clicks,
        add_ellipse_clicks,
        add_birange_clicks,
        suggest_clicks,
        ai_auto_gate_clicks,
        accept_clicks,
        reject_clicks,
        rename_clicks,
        toggle_clicks,
        delete_clicks,
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
        quadrant_gate_name,
        quadrant_x_threshold,
        quadrant_y_threshold,
        ellipse_gate_name,
        ellipse_center_x,
        ellipse_center_y,
        ellipse_radius_x,
        ellipse_radius_y,
        birange_gate_name,
        birange_x_min,
        birange_x_max,
        birange_y_min,
        birange_y_max,
        manage_gate_id,
        manage_gate_name,
        compensation_enabled,
    ):
        from dash import callback_context
        from app.core.gating import gate_to_table

        action = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        status = ""
        if action == "add-rectangle-gate":
            from app.core.gating import rectangle_gate

            if not all(value is not None for value in [x_channel, y_channel, x_min, x_max, y_min, y_max]):
                return no_update, no_update, no_update, "Choose x/y channels and complete all rectangle bounds.", no_update, no_update, no_update
            try:
                x_min_value, x_max_value, y_min_value, y_max_value = _parse_float_fields(
                    ("x min", x_min),
                    ("x max", x_max),
                    ("y min", y_min),
                    ("y max", y_max),
                )
            except ValueError as exc:
                return no_update, no_update, no_update, f"Rectangle gate needs numeric bounds: {exc}", no_update, no_update, no_update
            gate = rectangle_gate(
                uuid4().hex[:8],
                gate_name or "User rectangle gate",
                x_channel,
                y_channel,
                min(x_min_value, x_max_value),
                max(x_min_value, x_max_value),
                min(y_min_value, y_max_value),
                max(y_min_value, y_max_value),
            )
            sample = session.selected_sample(sample_id)
            use_compensation = _is_compensation_on(compensation_enabled) and sample is not None and sample.compensated_events is not None
            gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
            session.gates.append(gate)
            status = f"Added user-defined rectangle gate: {gate.name} ({gate.metadata['event_view']})."
        elif action == "add-review-current-view-gate":
            from app.core.compensation import event_view
            from app.core.gating import review_current_view_gate

            sample = session.selected_sample(sample_id)
            if sample is None:
                return no_update, no_update, no_update, "Upload and select a sample before adding a current-view review gate.", no_update, no_update, no_update
            use_compensation = _is_compensation_on(compensation_enabled) and sample.compensated_events is not None
            gate = review_current_view_gate(event_view(sample, use_compensation), x_channel, y_channel, uuid4().hex[:8])
            if gate is None:
                return no_update, no_update, no_update, "Current-view review gate could not be created; choose two numeric channels with enough events.", no_update, no_update, no_update
            gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
            session.gates.append(gate)
            status = f"Added editable current-view review gate: {gate.name}. Review/edit before relying on final statistics."
        elif action == "add-review-scatter-gate":
            from app.core.compensation import event_view
            from app.core.gating import review_scatter_gate

            sample = session.selected_sample(sample_id)
            if sample is None:
                return no_update, no_update, no_update, "Upload and select a sample before adding a review FSC/SSC gate.", no_update, no_update, no_update
            use_compensation = _is_compensation_on(compensation_enabled) and sample.compensated_events is not None
            gate = review_scatter_gate(event_view(sample, use_compensation), sample.channels, uuid4().hex[:8])
            if gate is None:
                return no_update, no_update, no_update, "FSC/SSC review gate could not be created; review channel inference first.", no_update, no_update, no_update
            gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
            session.gates.append(gate)
            status = f"Added editable FSC/SSC review gate: {gate.name}. Review/edit before relying on final statistics."
        elif action == "add-histogram-gate":
            from app.core.gating import histogram_range_gate

            if not all(value is not None for value in [hist_channel, hist_min, hist_max]):
                return no_update, no_update, no_update, "Choose a histogram channel and complete range bounds.", no_update, no_update, no_update
            try:
                hist_min_value, hist_max_value = _parse_float_fields(("min", hist_min), ("max", hist_max))
            except ValueError as exc:
                return no_update, no_update, no_update, f"Histogram gate needs numeric bounds: {exc}", no_update, no_update, no_update
            gate = histogram_range_gate(
                uuid4().hex[:8],
                hist_gate_name or "User histogram gate",
                hist_channel,
                min(hist_min_value, hist_max_value),
                max(hist_min_value, hist_max_value),
            )
            sample = session.selected_sample(sample_id)
            use_compensation = _is_compensation_on(compensation_enabled) and sample is not None and sample.compensated_events is not None
            gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
            session.gates.append(gate)
            status = f"Added user-defined histogram range gate: {gate.name} ({gate.metadata['event_view']})."
        elif action == "add-quadrant-gates":
            from app.core.gating import quadrant_gates

            if not all(value is not None for value in [x_channel, y_channel, quadrant_x_threshold, quadrant_y_threshold]):
                return no_update, no_update, no_update, "Choose x/y channels and complete quadrant thresholds.", no_update, no_update, no_update
            try:
                quadrant_x_value, quadrant_y_value = _parse_float_fields(
                    ("x threshold", quadrant_x_threshold),
                    ("y threshold", quadrant_y_threshold),
                )
            except ValueError as exc:
                return no_update, no_update, no_update, f"Quadrant gates need numeric thresholds: {exc}", no_update, no_update, no_update
            sample = session.selected_sample(sample_id)
            use_compensation = _is_compensation_on(compensation_enabled) and sample is not None and sample.compensated_events is not None
            event_view_name = "metadata_compensated" if use_compensation else "raw"
            gates = quadrant_gates(
                uuid4().hex[:8],
                quadrant_gate_name or "Quadrant gate",
                x_channel,
                y_channel,
                quadrant_x_value,
                quadrant_y_value,
                parent_id=_valid_parent_id(session.gates, manage_gate_id),
            )
            for gate in gates:
                gate.metadata["event_view"] = event_view_name
                gate.review_status = "review_needed"
            session.gates.extend(gates)
            status = f"Added four review-needed quadrant gates ({event_view_name})."
        elif action == "add-ellipse-gate":
            from app.core.gating import ellipse_gate

            if not all(value is not None for value in [x_channel, y_channel, ellipse_center_x, ellipse_center_y, ellipse_radius_x, ellipse_radius_y]):
                return no_update, no_update, no_update, "Choose x/y channels and complete ellipse center/radius values.", no_update, no_update, no_update
            try:
                ellipse_center_x_value, ellipse_center_y_value, ellipse_radius_x_value, ellipse_radius_y_value = _parse_float_fields(
                    ("center x", ellipse_center_x),
                    ("center y", ellipse_center_y),
                    ("radius x", ellipse_radius_x),
                    ("radius y", ellipse_radius_y),
                )
            except ValueError as exc:
                return no_update, no_update, no_update, f"Ellipse gate needs numeric center/radius values: {exc}", no_update, no_update, no_update
            gate = ellipse_gate(
                uuid4().hex[:8],
                ellipse_gate_name or "Ellipse gate",
                x_channel,
                y_channel,
                ellipse_center_x_value,
                ellipse_center_y_value,
                ellipse_radius_x_value,
                ellipse_radius_y_value,
                parent_id=_valid_parent_id(session.gates, manage_gate_id),
            )
            sample = session.selected_sample(sample_id)
            use_compensation = _is_compensation_on(compensation_enabled) and sample is not None and sample.compensated_events is not None
            gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
            gate.review_status = "review_needed"
            session.gates.append(gate)
            status = f"Added review-needed ellipse gate: {gate.name}."
        elif action == "add-birange-gate":
            from app.core.gating import bi_range_gate

            if not all(value is not None for value in [x_channel, y_channel, birange_x_min, birange_x_max, birange_y_min, birange_y_max]):
                return no_update, no_update, no_update, "Choose x/y channels and complete bi-range bounds.", no_update, no_update, no_update
            try:
                birange_x_min_value, birange_x_max_value, birange_y_min_value, birange_y_max_value = _parse_float_fields(
                    ("x min", birange_x_min),
                    ("x max", birange_x_max),
                    ("y min", birange_y_min),
                    ("y max", birange_y_max),
                )
            except ValueError as exc:
                return no_update, no_update, no_update, f"Bi-range gate needs numeric bounds: {exc}", no_update, no_update, no_update
            gate = bi_range_gate(
                uuid4().hex[:8],
                birange_gate_name or "Bi-range gate",
                x_channel,
                y_channel,
                min(birange_x_min_value, birange_x_max_value),
                max(birange_x_min_value, birange_x_max_value),
                min(birange_y_min_value, birange_y_max_value),
                max(birange_y_min_value, birange_y_max_value),
                parent_id=_valid_parent_id(session.gates, manage_gate_id),
            )
            sample = session.selected_sample(sample_id)
            use_compensation = _is_compensation_on(compensation_enabled) and sample is not None and sample.compensated_events is not None
            gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
            gate.review_status = "review_needed"
            session.gates.append(gate)
            status = f"Added review-needed bi-range gate: {gate.name}."
        elif action == "suggest-candidate-gates":
            from app.core.compensation import event_view
            from app.core.gating import suggest_candidate_gates

            sample = session.selected_sample(sample_id)
            if sample is None:
                return no_update, no_update, no_update, "Upload and select a sample before suggesting candidate gates.", no_update, no_update, no_update
            use_compensation = _is_compensation_on(compensation_enabled) and sample.compensated_events is not None
            current_view = "metadata_compensated" if use_compensation else "raw"
            existing_ids = {gate.gate_id for gate in session.gates}
            suggestions = [
                gate
                for gate in suggest_candidate_gates(event_view(sample, use_compensation), sample.channels, id_prefix=sample.sample_id)
                if gate.gate_id not in existing_ids
            ]
            for gate in suggestions:
                gate.metadata["event_view"] = current_view
            session.gates.extend(suggestions)
            status = (
                f"Added {len(suggestions)} disabled candidate gate(s) for review. Accept, edit, or reject before using them for final statistics."
                if suggestions
                else "No stable candidate gates were suggested for this sample."
            )
        elif action == "ai-auto-gate-clusters":
            from app.core.auto_gating import suggest_ai_auto_gates
            from app.core.vertex_gemini import label_clusters_with_gemini

            sample = session.selected_sample(sample_id)
            if sample is None:
                return no_update, no_update, no_update, "Upload and select a sample before running cluster-guided gate review.", no_update, no_update, no_update
            result = suggest_ai_auto_gates(
                sample,
                x_channel=x_channel,
                y_channel=y_channel,
                id_prefix=f"ai_{uuid4().hex[:6]}",
                labeler=label_clusters_with_gemini,
            )
            session.gates.extend(result.gates)
            status = _auto_gate_status(result.gates, result.warnings)
        elif action == "accept-candidate-gates":
            accepted = 0
            for gate in session.gates:
                if gate.candidate:
                    gate.candidate = False
                    gate.user_defined = True
                    gate.enabled = True
                    gate.review_status = "accepted"
                    gate.metadata["accepted_from_candidate"] = "true"
                    accepted += 1
            status = f"Accepted {accepted} candidate gate(s). Review/edit bounds before relying on final statistics."
        elif action == "reject-candidate-gates":
            before = len(session.gates)
            session.gates = [gate for gate in session.gates if not gate.candidate]
            status = f"Rejected {before - len(session.gates)} candidate gate(s)."
        elif action == "rename-gate":
            from app.core.gating import rename_gate

            gate = rename_gate(session.gates, manage_gate_id, manage_gate_name)
            status = f"Renamed gate to {gate.name}." if gate else "Select a gate and enter a non-empty name before renaming."
        elif action == "toggle-gate":
            from app.core.gating import toggle_gate_enabled

            gate = toggle_gate_enabled(session.gates, manage_gate_id)
            status = f"{'Enabled' if gate and gate.enabled else 'Disabled'} gate: {gate.name}." if gate else "Select a gate before toggling enabled state."
        elif action == "delete-gate":
            from app.core.gating import delete_gate

            session.gates, deleted = delete_gate(session.gates, manage_gate_id)
            status = "Deleted selected gate. Review any child gates that referenced it." if deleted else "Select a gate before deleting."
            manage_gate_id = None
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
                    logger.exception("Gate file could not be loaded from %s", GATES_PATH)
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
            from app.core.project_store import apply_project_sample_metadata, gates_from_project, load_project

            if PROJECT_PATH.exists():
                try:
                    project = load_project(PROJECT_PATH)
                    session.gates = gates_from_project(project)
                    session.comparison_rows = list(project.comparison_settings.get("comparison_rows", []))
                    restored_channels = apply_project_sample_metadata(session.sample_list(), project)
                    status = (
                        f"Loaded project metadata from {PROJECT_PATH}. Restored {len(session.gates)} gate(s); "
                        f"reapplied {restored_channels} channel annotation(s). Re-upload raw FCS/CSV files if samples are not already loaded."
                    )
                except Exception as exc:
                    logger.exception("Project file could not be loaded from %s", PROJECT_PATH)
                    status = f"Project file could not be loaded: {exc}"
            else:
                status = f"No saved project file found at {PROJECT_PATH}."
        sample = session.selected_sample(sample_id)
        stats = []
        if sample:
            from app.core.channel_labels import channel_label_map
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
            stats = gate_statistics(events, compatible_gates, masks, sample.fluorescence_channels, channel_label_map([sample]))
        if action == "export-gate-stats":
            from app.core.export_tables import export_rows_csv

            if stats:
                path = export_rows_csv(stats, EXPORT_ROOT / "gate-statistics.csv")
                status = f"Exported gate statistics CSV to {path}."
            else:
                status = "No gate statistics available to export."
        stats_columns = _columns_from_rows(stats, ["gate_name", "parent_gate", "channel_labels", "channels", "event_count", "percent_total", "percent_parent"])
        options = _gate_options(session.gates)
        selected_gate = manage_gate_id if manage_gate_id in {gate.gate_id for gate in session.gates} else (options[0]["value"] if options else None)
        return gate_to_table(session.gates), stats, table_columns(stats_columns), status, options, selected_gate, _gate_stack_cards(session.gates, stats)

    @app.callback(
        Output("gate-table", "data", allow_duplicate=True),
        Output("gate-stats-table", "data", allow_duplicate=True),
        Output("gate-stats-table", "columns", allow_duplicate=True),
        Output("gate-status", "children", allow_duplicate=True),
        Output("manage-gate-id", "options", allow_duplicate=True),
        Output("manage-gate-id", "value", allow_duplicate=True),
        Output("gate-stack-cards", "children", allow_duplicate=True),
        Output("last-drawn-gate-store", "data"),
        Input("scatter-graph", "relayoutData"),
        State("selected-sample-store", "data"),
        State("x-channel", "value"),
        State("y-channel", "value"),
        State("transform", "value"),
        State("cofactor", "value"),
        State("compensation-enabled", "value"),
        State("manage-gate-id", "value"),
        State("last-drawn-gate-store", "data"),
        prevent_initial_call=True,
    )
    def add_drawn_plot_gate(relayout_data, sample_id, x_channel, y_channel, transform, cofactor, compensation_enabled, manage_gate_id, last_signature):
        from app.core.gating import drawn_shape_gate, gate_to_table, latest_drawn_shape, shape_signature
        from app.core.plotting import _resolve_display_transform

        shape = latest_drawn_shape(relayout_data)
        if shape is None:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, last_signature
        signature = shape_signature(shape)
        if signature == last_signature:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, last_signature

        sample = session.selected_sample(sample_id)
        if sample is None:
            return no_update, no_update, no_update, "Upload and select a sample before drawing a gate.", no_update, no_update, no_update, signature

        use_compensation = _is_compensation_on(compensation_enabled) and sample.compensated_events is not None
        display_transform, _warnings = _resolve_display_transform(sample, transform or "raw", use_compensation)
        try:
            gate, _shape_signature = drawn_shape_gate(
                relayout_data,
                gate_id=uuid4().hex[:8],
                name=f"Drawn plot gate {len(session.gates) + 1}",
                x_channel=x_channel,
                y_channel=y_channel,
                transform=display_transform,
                cofactor=float(cofactor or 150),
                parent_id=_valid_parent_id(session.gates, manage_gate_id),
            )
        except Exception as exc:
            logger.exception("Drawn gate could not be created")
            return no_update, no_update, no_update, f"Drawn gate could not be created: {exc}", no_update, no_update, no_update, signature
        if gate is None:
            return no_update, no_update, no_update, "Draw a rectangle or closed polygon on the scatter plot to create a gate.", no_update, no_update, no_update, signature

        gate.metadata["event_view"] = "metadata_compensated" if use_compensation else "raw"
        gate.metadata["source_sample_id"] = sample.sample_id
        session.gates.append(gate)
        stats = _stats_for_sample(session, sample_id, compensation_enabled)
        stats_columns = _columns_from_rows(stats, ["gate_name", "parent_gate", "channel_labels", "channels", "event_count", "percent_total", "percent_parent"])
        options = _gate_options(session.gates)
        return (
            gate_to_table(session.gates),
            stats,
            table_columns(stats_columns),
            _drawn_gate_status(gate),
            options,
            gate.gate_id,
            _gate_stack_cards(session.gates, stats),
            signature,
        )


def _columns_from_rows(rows: list[dict[str, object]], preferred: list[str]) -> list[str]:
    seen = list(preferred)
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


def _is_compensation_on(value) -> bool:
    return isinstance(value, list) and "on" in value


def _parse_float_fields(*fields: tuple[str, object]) -> tuple[float, ...]:
    values: list[float] = []
    for label, value in fields:
        if value is None or value == "":
            raise ValueError(f"{label} is required")
        try:
            values.append(float(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be numeric") from exc
    return tuple(values)


def _gate_options(gates):
    return [{"label": f"{gate.name} ({gate.gate_id})", "value": gate.gate_id} for gate in gates]


def _valid_parent_id(gates, gate_id: str | None) -> str | None:
    if not gate_id:
        return None
    return gate_id if any(gate.gate_id == gate_id for gate in gates) else None


def _drawn_gate_status(gate) -> str:
    parent = f" as child of {gate.parent_id}" if gate.parent_id else " at total-events level"
    return f"Added review-needed {gate.gate_type} gate from plot drawing{parent}: {gate.name}. Review/edit before relying on final statistics."


def _auto_gate_status(gates, warnings: list[str]) -> str:
    if not gates:
        return "Cluster-guided gate review did not add gates. " + " ".join(warnings)
    enhanced = sum(gate.metadata.get("label_source") == "enhanced_assistant" for gate in gates)
    note = f" Enhanced labels applied to {enhanced} cluster(s)." if enhanced else ""
    warning_text = " ".join(warnings)
    return (
        f"Added {len(gates)} disabled review-needed cluster gate candidate(s) from cluster footprints."
        f"{note} Review/edit and accept before using final statistics. {warning_text}"
    ).strip()


def _stats_for_sample(session: WorkbenchSession, sample_id: str | None, compensation_enabled) -> list[dict[str, object]]:
    sample = session.selected_sample(sample_id)
    if sample is None:
        return []
    from app.core.channel_labels import channel_label_map
    from app.core.compensation import event_view
    from app.core.gating import apply_gate_tree
    from app.core.stats import gate_statistics

    use_compensation = _is_compensation_on(compensation_enabled) and sample.compensated_events is not None
    events = event_view(sample, use_compensation)
    compatible_gates = [
        gate
        for gate in session.gates
        if gate.metadata.get("event_view", "raw") == ("metadata_compensated" if use_compensation else "raw")
    ]
    masks = apply_gate_tree(events, compatible_gates)
    return gate_statistics(events, compatible_gates, masks, sample.fluorescence_channels, channel_label_map([sample]))


def _gate_stack_cards(gates, stats: list[dict[str, object]]):
    if not gates:
        return html.Div("No gates yet. Add or suggest review-needed gates.", className="gate-stack-card empty")
    stats_by_gate = {row.get("gate_id"): row for row in stats}
    cards = []
    for gate in gates:
        row = stats_by_gate.get(gate.gate_id, {})
        count = row.get("event_count")
        percent_total = row.get("percent_total")
        percent_parent = row.get("percent_parent")
        warning = gate.metadata.get("mask_warning") or row.get("gate_warning") or ""
        status = _gate_status_label(gate)
        children = [
            html.Div(
                [
                    html.Span(status, className="gate-stack-status"),
                    html.Strong(gate.name),
                ],
                className="gate-stack-head",
            ),
            html.Small(f"{gate.gate_type} | parent: {gate.parent_id or 'total'} | {row.get('channel_labels') or ', '.join(gate.channels)}"),
            html.Div(
                [
                    html.Span(f"{_format_stat(count)} events"),
                    html.Span(f"{_format_stat(percent_total)}% total"),
                    html.Span(f"{_format_stat(percent_parent)}% parent"),
                ],
                className="gate-stack-metrics",
            ),
        ]
        if warning:
            children.append(html.P(warning, className="gate-stack-warning"))
        cards.append(
            html.Div(
                children,
                className=f"gate-stack-card {'disabled' if not gate.enabled else ''} {'candidate' if gate.candidate else ''}".strip(),
            )
        )
    return cards


def _gate_status_label(gate) -> str:
    if gate.candidate:
        return "candidate review needed"
    if not gate.enabled:
        return "disabled"
    if gate.review_status and gate.review_status != "accepted":
        return gate.review_status.replace("_", " ")
    return "active"


def _format_stat(value: object) -> str:
    if value is None or value == "":
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3g}"
    return str(value)
