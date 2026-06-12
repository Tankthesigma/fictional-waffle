from __future__ import annotations

import base64
import json

from app.main import create_app


def _callback_key(app, contains: str) -> str:
    for key in app.callback_map:
        if contains in key:
            return key
    raise AssertionError(f"callback containing {contains!r} was not registered")


def _gate_callback_payload(output: str, action_id: str, state_updates: dict[str, object] | None = None) -> dict[str, object]:
    input_ids = [
        "add-rectangle-gate",
        "add-review-current-view-gate",
        "add-review-scatter-gate",
        "add-histogram-gate",
        "add-quadrant-gates",
        "add-ellipse-gate",
        "add-birange-gate",
        "suggest-candidate-gates",
        "accept-candidate-gates",
        "reject-candidate-gates",
        "rename-gate",
        "toggle-gate",
        "delete-gate",
        "save-gates",
        "load-gates",
        "save-project",
        "load-project",
        "export-gate-stats",
    ]
    state_values: dict[str, object] = {
        "selected-sample-store": None,
        "x-channel": "FSC-A",
        "y-channel": "SSC-A",
        "hist-channel": "FL1-A",
        "plot-mode": "scatter",
        "transform": "raw",
        "cofactor": 150,
        "max-events": 50000,
        "control-group": "",
        "treated-group": "",
        "gate-name": "main",
        "gate-x-min": 0,
        "gate-x-max": 1,
        "gate-y-min": 0,
        "gate-y-max": 1,
        "hist-gate-name": "positive",
        "hist-gate-min": 0,
        "hist-gate-max": 1,
        "quadrant-gate-name": "quad",
        "quadrant-x-threshold": 1,
        "quadrant-y-threshold": 1,
        "ellipse-gate-name": "ellipse",
        "ellipse-center-x": 1,
        "ellipse-center-y": 1,
        "ellipse-radius-x": 1,
        "ellipse-radius-y": 1,
        "birange-gate-name": "birange",
        "birange-x-min": 0,
        "birange-x-max": 1,
        "birange-y-min": 0,
        "birange-y-max": 1,
        "manage-gate-id": None,
        "manage-gate-name": "",
        "compensation-enabled": [],
    }
    state_values.update(state_updates or {})
    state_order = [
        "selected-sample-store",
        "x-channel",
        "y-channel",
        "hist-channel",
        "plot-mode",
        "transform",
        "cofactor",
        "max-events",
        "control-group",
        "treated-group",
        "gate-name",
        "gate-x-min",
        "gate-x-max",
        "gate-y-min",
        "gate-y-max",
        "hist-gate-name",
        "hist-gate-min",
        "hist-gate-max",
        "quadrant-gate-name",
        "quadrant-x-threshold",
        "quadrant-y-threshold",
        "ellipse-gate-name",
        "ellipse-center-x",
        "ellipse-center-y",
        "ellipse-radius-x",
        "ellipse-radius-y",
        "birange-gate-name",
        "birange-x-min",
        "birange-x-max",
        "birange-y-min",
        "birange-y-max",
        "manage-gate-id",
        "manage-gate-name",
        "compensation-enabled",
    ]
    return {
        "output": output,
        "outputs": [
            {"id": "gate-table", "property": "data"},
            {"id": "gate-stats-table", "property": "data"},
            {"id": "gate-stats-table", "property": "columns"},
            {"id": "gate-status", "property": "children"},
            {"id": "manage-gate-id", "property": "options"},
            {"id": "manage-gate-id", "property": "value"},
            {"id": "gate-stack-cards", "property": "children"},
        ],
        "inputs": [{"id": input_id, "property": "n_clicks", "value": 1 if input_id == action_id else 0} for input_id in input_ids],
        "state": [{"id": state_id, "property": "value", "value": state_values[state_id]} for state_id in state_order],
        "changedPropIds": [f"{action_id}.n_clicks"],
    }


def test_incomplete_gate_form_returns_status_without_callback_error():
    dash_app = create_app()
    client = dash_app.server.test_client()
    output = _callback_key(dash_app, "gate-status.children")

    response = client.post(
        "/_dash-update-component",
        json={
            "output": output,
            "outputs": [
                {"id": "gate-table", "property": "data"},
                {"id": "gate-stats-table", "property": "data"},
                {"id": "gate-stats-table", "property": "columns"},
                {"id": "gate-status", "property": "children"},
                {"id": "manage-gate-id", "property": "options"},
                {"id": "manage-gate-id", "property": "value"},
                {"id": "gate-stack-cards", "property": "children"},
            ],
            "inputs": [
                {"id": "add-rectangle-gate", "property": "n_clicks", "value": 1},
                {"id": "add-review-current-view-gate", "property": "n_clicks", "value": 0},
                {"id": "add-review-scatter-gate", "property": "n_clicks", "value": 0},
                {"id": "add-histogram-gate", "property": "n_clicks", "value": 0},
                {"id": "add-quadrant-gates", "property": "n_clicks", "value": 0},
                {"id": "add-ellipse-gate", "property": "n_clicks", "value": 0},
                {"id": "add-birange-gate", "property": "n_clicks", "value": 0},
                {"id": "suggest-candidate-gates", "property": "n_clicks", "value": 0},
                {"id": "accept-candidate-gates", "property": "n_clicks", "value": 0},
                {"id": "reject-candidate-gates", "property": "n_clicks", "value": 0},
                {"id": "rename-gate", "property": "n_clicks", "value": 0},
                {"id": "toggle-gate", "property": "n_clicks", "value": 0},
                {"id": "delete-gate", "property": "n_clicks", "value": 0},
                {"id": "save-gates", "property": "n_clicks", "value": 0},
                {"id": "load-gates", "property": "n_clicks", "value": 0},
                {"id": "save-project", "property": "n_clicks", "value": 0},
                {"id": "load-project", "property": "n_clicks", "value": 0},
                {"id": "export-gate-stats", "property": "n_clicks", "value": 0},
            ],
            "state": [
                {"id": "selected-sample-store", "property": "data", "value": None},
                {"id": "x-channel", "property": "value", "value": "FSC-A"},
                {"id": "y-channel", "property": "value", "value": "SSC-A"},
                {"id": "hist-channel", "property": "value", "value": "FL1-A"},
                {"id": "plot-mode", "property": "value", "value": "scatter"},
                {"id": "transform", "property": "value", "value": "raw"},
                {"id": "cofactor", "property": "value", "value": 150},
                {"id": "max-events", "property": "value", "value": 50000},
                {"id": "control-group", "property": "value", "value": ""},
                {"id": "treated-group", "property": "value", "value": ""},
                {"id": "gate-name", "property": "value", "value": "main"},
                {"id": "gate-x-min", "property": "value", "value": None},
                {"id": "gate-x-max", "property": "value", "value": None},
                {"id": "gate-y-min", "property": "value", "value": None},
                {"id": "gate-y-max", "property": "value", "value": None},
                {"id": "hist-gate-name", "property": "value", "value": "positive"},
                {"id": "hist-gate-min", "property": "value", "value": None},
                {"id": "hist-gate-max", "property": "value", "value": None},
                {"id": "quadrant-gate-name", "property": "value", "value": "quad"},
                {"id": "quadrant-x-threshold", "property": "value", "value": None},
                {"id": "quadrant-y-threshold", "property": "value", "value": None},
                {"id": "ellipse-gate-name", "property": "value", "value": "ellipse"},
                {"id": "ellipse-center-x", "property": "value", "value": None},
                {"id": "ellipse-center-y", "property": "value", "value": None},
                {"id": "ellipse-radius-x", "property": "value", "value": None},
                {"id": "ellipse-radius-y", "property": "value", "value": None},
                {"id": "birange-gate-name", "property": "value", "value": "birange"},
                {"id": "birange-x-min", "property": "value", "value": None},
                {"id": "birange-x-max", "property": "value", "value": None},
                {"id": "birange-y-min", "property": "value", "value": None},
                {"id": "birange-y-max", "property": "value", "value": None},
                {"id": "manage-gate-id", "property": "value", "value": None},
                {"id": "manage-gate-name", "property": "value", "value": ""},
                {"id": "compensation-enabled", "property": "value", "value": []},
            ],
            "changedPropIds": ["add-rectangle-gate.n_clicks"],
        },
    )

    assert response.status_code == 200
    assert "complete all rectangle bounds" in response.get_data(as_text=True)


def test_incomplete_histogram_gate_form_returns_status_without_callback_error():
    dash_app = create_app()
    client = dash_app.server.test_client()
    output = _callback_key(dash_app, "gate-status.children")

    response = client.post(
        "/_dash-update-component",
        json={
            "output": output,
            "outputs": [
                {"id": "gate-table", "property": "data"},
                {"id": "gate-stats-table", "property": "data"},
                {"id": "gate-stats-table", "property": "columns"},
                {"id": "gate-status", "property": "children"},
                {"id": "manage-gate-id", "property": "options"},
                {"id": "manage-gate-id", "property": "value"},
                {"id": "gate-stack-cards", "property": "children"},
            ],
            "inputs": [
                {"id": "add-rectangle-gate", "property": "n_clicks", "value": 0},
                {"id": "add-review-current-view-gate", "property": "n_clicks", "value": 0},
                {"id": "add-review-scatter-gate", "property": "n_clicks", "value": 0},
                {"id": "add-histogram-gate", "property": "n_clicks", "value": 1},
                {"id": "add-quadrant-gates", "property": "n_clicks", "value": 0},
                {"id": "add-ellipse-gate", "property": "n_clicks", "value": 0},
                {"id": "add-birange-gate", "property": "n_clicks", "value": 0},
                {"id": "suggest-candidate-gates", "property": "n_clicks", "value": 0},
                {"id": "accept-candidate-gates", "property": "n_clicks", "value": 0},
                {"id": "reject-candidate-gates", "property": "n_clicks", "value": 0},
                {"id": "rename-gate", "property": "n_clicks", "value": 0},
                {"id": "toggle-gate", "property": "n_clicks", "value": 0},
                {"id": "delete-gate", "property": "n_clicks", "value": 0},
                {"id": "save-gates", "property": "n_clicks", "value": 0},
                {"id": "load-gates", "property": "n_clicks", "value": 0},
                {"id": "save-project", "property": "n_clicks", "value": 0},
                {"id": "load-project", "property": "n_clicks", "value": 0},
                {"id": "export-gate-stats", "property": "n_clicks", "value": 0},
            ],
            "state": [
                {"id": "selected-sample-store", "property": "data", "value": None},
                {"id": "x-channel", "property": "value", "value": "FSC-A"},
                {"id": "y-channel", "property": "value", "value": "SSC-A"},
                {"id": "hist-channel", "property": "value", "value": "FL1-A"},
                {"id": "plot-mode", "property": "value", "value": "scatter"},
                {"id": "transform", "property": "value", "value": "raw"},
                {"id": "cofactor", "property": "value", "value": 150},
                {"id": "max-events", "property": "value", "value": 50000},
                {"id": "control-group", "property": "value", "value": ""},
                {"id": "treated-group", "property": "value", "value": ""},
                {"id": "gate-name", "property": "value", "value": "main"},
                {"id": "gate-x-min", "property": "value", "value": 0},
                {"id": "gate-x-max", "property": "value", "value": 1},
                {"id": "gate-y-min", "property": "value", "value": 0},
                {"id": "gate-y-max", "property": "value", "value": 1},
                {"id": "hist-gate-name", "property": "value", "value": "positive"},
                {"id": "hist-gate-min", "property": "value", "value": None},
                {"id": "hist-gate-max", "property": "value", "value": None},
                {"id": "quadrant-gate-name", "property": "value", "value": "quad"},
                {"id": "quadrant-x-threshold", "property": "value", "value": None},
                {"id": "quadrant-y-threshold", "property": "value", "value": None},
                {"id": "ellipse-gate-name", "property": "value", "value": "ellipse"},
                {"id": "ellipse-center-x", "property": "value", "value": None},
                {"id": "ellipse-center-y", "property": "value", "value": None},
                {"id": "ellipse-radius-x", "property": "value", "value": None},
                {"id": "ellipse-radius-y", "property": "value", "value": None},
                {"id": "birange-gate-name", "property": "value", "value": "birange"},
                {"id": "birange-x-min", "property": "value", "value": None},
                {"id": "birange-x-max", "property": "value", "value": None},
                {"id": "birange-y-min", "property": "value", "value": None},
                {"id": "birange-y-max", "property": "value", "value": None},
                {"id": "manage-gate-id", "property": "value", "value": None},
                {"id": "manage-gate-name", "property": "value", "value": ""},
                {"id": "compensation-enabled", "property": "value", "value": []},
            ],
            "changedPropIds": ["add-histogram-gate.n_clicks"],
        },
    )

    assert response.status_code == 200
    assert "complete range bounds" in response.get_data(as_text=True)


def test_non_numeric_ellipse_gate_form_returns_status_without_callback_error():
    dash_app = create_app()
    client = dash_app.server.test_client()
    output = _callback_key(dash_app, "gate-status.children")

    response = client.post(
        "/_dash-update-component",
        json=_gate_callback_payload(output, "add-ellipse-gate", {"ellipse-radius-x": "wide"}),
    )

    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Ellipse gate needs numeric center" in text
    assert "radius x must be numeric" in text


def test_bad_upload_payload_returns_friendly_status_without_callback_error():
    dash_app = create_app()
    client = dash_app.server.test_client()
    output = _callback_key(dash_app, "upload-status.children")

    response = client.post(
        "/_dash-update-component",
        json={
            "output": output,
            "outputs": [
                {"id": "upload-status", "property": "children"},
                {"id": "sample-table", "property": "data"},
                {"id": "sample-dropdown", "property": "options"},
                {"id": "sample-dropdown", "property": "value"},
                {"id": "sample-ids-store", "property": "data"},
                {"id": "metric-samples", "property": "children"},
                {"id": "metric-events", "property": "children"},
                {"id": "metric-flags", "property": "children"},
            ],
            "inputs": [
                {"id": "clear-project", "property": "n_clicks", "value": 0},
                {"id": "load-demo-data", "property": "n_clicks", "value": 0},
                {"id": "upload-data", "property": "contents", "value": ["data:application/octet-stream;base64,not-base64"]},
                {"id": "upload-manifest", "property": "contents", "value": None},
                {"id": "upload-panel", "property": "contents", "value": None},
            ],
            "state": [
                {"id": "upload-data", "property": "filename", "value": ["bad.fcs"]},
                {"id": "upload-manifest", "property": "filename", "value": None},
                {"id": "upload-panel", "property": "filename", "value": None},
            ],
            "changedPropIds": ["upload-data.contents"],
        },
    )

    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "valid base64" in text
    assert "bad.fcs" in text


def test_clear_project_callback_resets_visible_tables():
    dash_app = create_app()
    client = dash_app.server.test_client()
    output = _callback_key(dash_app, "upload-status.children")

    response = client.post(
        "/_dash-update-component",
        json={
            "output": output,
            "outputs": _upload_outputs(),
            "inputs": [
                {"id": "clear-project", "property": "n_clicks", "value": 1},
                {"id": "load-demo-data", "property": "n_clicks", "value": 0},
                {"id": "upload-data", "property": "contents", "value": None},
                {"id": "upload-manifest", "property": "contents", "value": None},
                {"id": "upload-panel", "property": "contents", "value": None},
            ],
            "state": [
                {"id": "upload-data", "property": "filename", "value": None},
                {"id": "upload-manifest", "property": "filename", "value": None},
                {"id": "upload-panel", "property": "filename", "value": None},
            ],
            "changedPropIds": ["clear-project.n_clicks"],
        },
    )

    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Project cleared" in text
    assert '"sample-table"' in text


def test_csv_upload_callback_populates_sample_table():
    dash_app = create_app()
    client = dash_app.server.test_client()
    output = _callback_key(dash_app, "upload-status.children")
    encoded = base64.b64encode(b"FSC-A,SSC-A,FL1-A\n1,2,10\n2,4,20\n3,8,30\n4,16,40\n5,32,50\n6,64,60\n7,128,70\n8,256,80\n9,512,90\n10,1024,100\n").decode()

    response = client.post(
        "/_dash-update-component",
        json={
            "output": output,
            "outputs": _upload_outputs(),
            "inputs": [
                {"id": "clear-project", "property": "n_clicks", "value": 0},
                {"id": "load-demo-data", "property": "n_clicks", "value": 0},
                {"id": "upload-data", "property": "contents", "value": [f"data:text/csv;base64,{encoded}"]},
                {"id": "upload-manifest", "property": "contents", "value": None},
                {"id": "upload-panel", "property": "contents", "value": None},
            ],
            "state": [
                {"id": "upload-data", "property": "filename", "value": ["demo.csv"]},
                {"id": "upload-manifest", "property": "filename", "value": None},
                {"id": "upload-panel", "property": "filename", "value": None},
            ],
            "changedPropIds": ["upload-data.contents"],
        },
    )

    assert response.status_code == 200
    payload = json.loads(response.get_data(as_text=True))
    sample_rows = payload["response"]["sample-table"]["data"]
    assert sample_rows[0]["sample_id"] == "demo"
    assert sample_rows[0]["event_count"] == 10


def test_load_demo_dataset_callback_populates_batch_without_files():
    dash_app = create_app()
    client = dash_app.server.test_client()
    output = _callback_key(dash_app, "upload-status.children")

    response = client.post(
        "/_dash-update-component",
        json={
            "output": output,
            "outputs": _upload_outputs(),
            "inputs": [
                {"id": "clear-project", "property": "n_clicks", "value": 0},
                {"id": "load-demo-data", "property": "n_clicks", "value": 1},
                {"id": "upload-data", "property": "contents", "value": None},
                {"id": "upload-manifest", "property": "contents", "value": None},
                {"id": "upload-panel", "property": "contents", "value": None},
            ],
            "state": [
                {"id": "upload-data", "property": "filename", "value": None},
                {"id": "upload-manifest", "property": "filename", "value": None},
                {"id": "upload-panel", "property": "filename", "value": None},
            ],
            "changedPropIds": ["load-demo-data.n_clicks"],
        },
    )

    assert response.status_code == 200
    payload = json.loads(response.get_data(as_text=True))
    sample_rows = payload["response"]["sample-table"]["data"]
    assert len(sample_rows) == 4
    assert sample_rows[0]["sample_id"] == "demo_control_1"
    assert payload["response"]["metric-samples"]["children"] == "4"
    assert "synthetic demo dataset" in response.get_data(as_text=True)


def _upload_outputs():
    return [
        {"id": "upload-status", "property": "children"},
        {"id": "sample-table", "property": "data"},
        {"id": "sample-dropdown", "property": "options"},
        {"id": "sample-dropdown", "property": "value"},
        {"id": "sample-ids-store", "property": "data"},
        {"id": "metric-samples", "property": "children"},
        {"id": "metric-events", "property": "children"},
        {"id": "metric-flags", "property": "children"},
    ]
