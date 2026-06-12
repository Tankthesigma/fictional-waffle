from __future__ import annotations

import base64
import logging
from pathlib import Path
import shutil
from uuid import uuid4

from dash import Input, Output, State, callback_context, html, no_update

from app.core.paths import UPLOAD_ROOT
from app.core.session_store import WorkbenchSession

logger = logging.getLogger(__name__)


def register_upload_callbacks(app, session: WorkbenchSession) -> None:
    @app.callback(
        Output("upload-status", "children"),
        Output("sample-table", "data"),
        Output("sample-dropdown", "options"),
        Output("sample-dropdown", "value"),
        Output("sample-ids-store", "data"),
        Output("metric-samples", "children"),
        Output("metric-events", "children"),
        Output("metric-flags", "children"),
        Input("clear-project", "n_clicks"),
        Input("load-demo-data", "n_clicks"),
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
        Input("upload-manifest", "contents"),
        State("upload-manifest", "filename"),
        Input("upload-panel", "contents"),
        State("upload-panel", "filename"),
        prevent_initial_call=True,
    )
    def handle_upload(clear_clicks, demo_clicks, contents, filenames, manifest_contents, manifest_filename, panel_contents, panel_filename):
        from app.core.demo_data import build_demo_samples
        from app.core.csv_loader import apply_manifest, load_csv_file, parse_manifest
        from app.core.fcs_loader import load_fcs_file
        from app.core.panel_setup import apply_panel_setup, parse_panel_setup
        from app.core.qc import qc_summary, run_batch_qc

        action = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        if action == "clear-project":
            session.samples.clear()
            session.gates.clear()
            session.qc_flags.clear()
            session.comparison_rows.clear()
            _clear_upload_cache()
            return html.Div("Project cleared."), [], [], None, [], "0", "0", "0"
        if action == "load-demo-data":
            _clear_session(session)
            _clear_upload_cache()
            project_dir = UPLOAD_ROOT / f"demo-{uuid4().hex[:8]}"
            loaded = build_demo_samples(project_dir)
            for sample in loaded:
                session.samples[sample.sample_id] = sample
            session.qc_flags = run_batch_qc(session.sample_list())
            messages = [
                "Loaded deterministic local synthetic demo dataset.",
                "Demo samples are for workflow testing only and are not biological reference data.",
            ]
            return _upload_response(session, messages, qc_summary)
        if not contents and not manifest_contents and not panel_contents:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        filenames = filenames or []
        if isinstance(contents, str):
            contents = [contents]
        if isinstance(filenames, str):
            filenames = [filenames]
        project_dir = UPLOAD_ROOT / uuid4().hex[:12]
        project_dir.mkdir(parents=True, exist_ok=True)

        loaded = []
        messages = []
        for content, filename in zip(contents or [], filenames, strict=False):
            if not filename:
                messages.append("Skipped an upload without a filename.")
                continue
            suffix = Path(filename).suffix.lower()
            if suffix not in {".fcs", ".csv"}:
                messages.append(f"Skipped {filename}: only .fcs and .csv files are supported.")
                continue
            try:
                path = _save_upload(content, filename, project_dir)
            except ValueError as exc:
                messages.append(f"Skipped {filename}: {exc}")
                continue
            result = load_fcs_file(path) if suffix == ".fcs" else load_csv_file(path)
            if result.sample:
                loaded.append(result.sample)
                messages.extend(result.warnings)
                if result.sample.compensated_events is not None:
                    messages.append(
                        f"{result.sample.filename}: metadata compensation available for {len(result.sample.spillover.channels)} channel(s)."
                    )
                elif result.sample.spillover is not None:
                    messages.extend(f"{result.sample.filename}: {warning}" for warning in result.sample.compensation_warnings)
            messages.extend(result.errors)

        manifest = {}
        if manifest_contents and manifest_filename:
            try:
                manifest_path = _save_upload(manifest_contents, manifest_filename, project_dir)
                manifest = parse_manifest(manifest_path)
                apply_manifest(loaded or session.sample_list(), manifest)
                messages.append(f"Applied manifest: {manifest_filename}.")
            except Exception as exc:
                logger.exception("Manifest upload could not be applied: %s", manifest_filename)
                messages.append(f"Manifest was not applied: {exc}")

        if panel_contents and panel_filename:
            try:
                panel_path = _save_upload(panel_contents, panel_filename, project_dir)
                panel = parse_panel_setup(panel_path)
                messages.extend(apply_panel_setup(loaded or session.sample_list(), panel))
                messages.append(f"Applied panel setup: {panel_filename}.")
            except Exception as exc:
                logger.exception("Panel setup upload could not be applied: %s", panel_filename)
                messages.append(f"Panel setup was not applied: {exc}")

        for sample in loaded:
            session.samples[sample.sample_id] = sample
        session.qc_flags = run_batch_qc(session.sample_list())
        return _upload_response(session, messages or [f"Loaded {len(loaded)} sample(s)."], qc_summary)


def _save_upload(content: str, filename: str, directory: Path) -> Path:
    try:
        _header, encoded = content.split(",", 1)
        data = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        logger.exception("Upload payload for %s was not valid base64 data", filename)
        raise ValueError("upload payload was not valid base64 data") from exc
    safe = Path(filename).name
    target = directory / safe
    target.write_bytes(data)
    return target


def _clear_upload_cache() -> None:
    if not UPLOAD_ROOT.exists():
        return
    for child in UPLOAD_ROOT.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        elif child.is_file():
            child.unlink(missing_ok=True)


def _clear_session(session: WorkbenchSession) -> None:
    session.samples.clear()
    session.gates.clear()
    session.qc_flags.clear()
    session.comparison_rows.clear()


def _upload_response(session: WorkbenchSession, messages: list[str], qc_summary):
    sample_rows = [
        sample.to_summary_dict(qc_summary(session.qc_flags.get(sample.sample_id, [])))
        for sample in session.sample_list()
    ]
    options = [{"label": f"{sample.sample_id} ({sample.filename})", "value": sample.sample_id} for sample in session.sample_list()]
    selected = options[0]["value"] if options else None
    total_events = sum(sample.event_count for sample in session.sample_list())
    status = html.Ul([html.Li(message) for message in messages])
    return (
        status,
        sample_rows,
        options,
        selected,
        [option["value"] for option in options],
        str(len(session.samples)),
        f"{total_events:,}",
        str(len(session.all_qc_flags())),
    )
