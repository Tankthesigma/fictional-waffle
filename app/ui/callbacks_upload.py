from __future__ import annotations

import base64
from pathlib import Path
from uuid import uuid4

from dash import Input, Output, State, html, no_update

from app.core.csv_loader import apply_manifest, load_csv_file, parse_manifest
from app.core.fcs_loader import load_fcs_file
from app.core.qc import qc_summary, run_batch_qc
from app.core.session_store import WorkbenchSession

UPLOAD_ROOT = Path("app_data/uploads")


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
        Input("upload-data", "contents"),
        State("upload-data", "filename"),
        Input("upload-manifest", "contents"),
        State("upload-manifest", "filename"),
        prevent_initial_call=True,
    )
    def handle_upload(contents, filenames, manifest_contents, manifest_filename):
        if not contents:
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
        for content, filename in zip(contents, filenames, strict=False):
            suffix = Path(filename).suffix.lower()
            if suffix not in {".fcs", ".csv"}:
                messages.append(f"Skipped {filename}: only .fcs and .csv files are supported.")
                continue
            path = _save_upload(content, filename, project_dir)
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
                apply_manifest(loaded, manifest)
                messages.append(f"Applied manifest: {manifest_filename}.")
            except Exception as exc:
                messages.append(f"Manifest was not applied: {exc}")

        for sample in loaded:
            session.samples[sample.sample_id] = sample
        session.qc_flags = run_batch_qc(session.sample_list())
        sample_rows = [
            sample.to_summary_dict(qc_summary(session.qc_flags.get(sample.sample_id, [])))
            for sample in session.sample_list()
        ]
        options = [{"label": f"{sample.sample_id} ({sample.filename})", "value": sample.sample_id} for sample in session.sample_list()]
        selected = options[0]["value"] if options else None
        total_events = sum(sample.event_count for sample in session.sample_list())
        status = html.Ul([html.Li(message) for message in messages] or [html.Li(f"Loaded {len(loaded)} sample(s).")])
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


def _save_upload(content: str, filename: str, directory: Path) -> Path:
    header, encoded = content.split(",", 1)
    data = base64.b64decode(encoded)
    safe = Path(filename).name
    target = directory / safe
    target.write_bytes(data)
    return target
