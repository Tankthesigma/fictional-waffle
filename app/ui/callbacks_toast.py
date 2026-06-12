from __future__ import annotations

from dash import Input, Output, callback_context, html, no_update


def register_toast_callbacks(app) -> None:
    @app.callback(
        Output("toast-store", "data"),
        Output("toast-timer", "disabled"),
        Input("upload-status", "children"),
        Input("gate-status", "children"),
        Input("template-status", "children"),
        Input("plot-preset-status", "children"),
        Input("role-override-status", "children"),
        Input("compensation-status", "children"),
        Input("compare-status", "children"),
        Input("report-status", "children"),
        Input("toast-timer", "n_intervals"),
        prevent_initial_call=True,
    )
    def update_toast_store(*values):
        triggered = callback_context.triggered_id
        if triggered == "toast-timer":
            return None, True
        message = _toast_text(values[_STATUS_IDS.index(triggered)]) if triggered in _STATUS_IDS else ""
        if not message:
            return no_update, no_update
        return {"title": _toast_title(triggered), "message": message, "kind": _toast_kind(message)}, False

    @app.callback(Output("toast-container", "children"), Input("toast-store", "data"))
    def render_toast(data):
        if not isinstance(data, dict) or not data.get("message"):
            return []
        return html.Div(
            [html.Strong(data.get("title") or "Workbench"), html.Span(data["message"])],
            className=f"toast {data.get('kind') or 'info'}",
        )


_STATUS_IDS = [
    "upload-status",
    "gate-status",
    "template-status",
    "plot-preset-status",
    "role-override-status",
    "compensation-status",
    "compare-status",
    "report-status",
]


def _toast_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(filter(None, (_toast_text(item) for item in value))).strip()
    props = getattr(value, "props", None)
    if isinstance(props, dict):
        return _toast_text(props.get("children"))
    if isinstance(value, dict):
        return _toast_text(value.get("props", {}).get("children") or value.get("children"))
    return str(value).strip()


def _toast_title(triggered_id: str | None) -> str:
    return {
        "upload-status": "Import",
        "gate-status": "Gate Review",
        "template-status": "Template",
        "plot-preset-status": "Plot Preset",
        "role-override-status": "Channel Role",
        "compensation-status": "Compensation",
        "compare-status": "Comparison",
        "report-status": "Report",
    }.get(str(triggered_id), "Workbench")


def _toast_kind(message: str) -> str:
    lower = message.lower()
    if any(token in lower for token in ("could not", "failed", "not applied", "skipped", "no ")):
        return "review"
    if any(token in lower for token in ("exported", "saved", "loaded", "applied", "added", "accepted")):
        return "ok"
    return "info"
