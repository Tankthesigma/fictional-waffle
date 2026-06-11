from __future__ import annotations

import base64
import json

from app.main import create_app


def _callback_key(app, contains: str) -> str:
    for key in app.callback_map:
        if contains in key:
            return key
    raise AssertionError(f"callback containing {contains!r} was not registered")


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
                {"id": "add-histogram-gate", "property": "n_clicks", "value": 0},
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
                {"id": "add-histogram-gate", "property": "n_clicks", "value": 1},
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
                {"id": "manage-gate-id", "property": "value", "value": None},
                {"id": "manage-gate-name", "property": "value", "value": ""},
                {"id": "compensation-enabled", "property": "value", "value": []},
            ],
            "changedPropIds": ["add-histogram-gate.n_clicks"],
        },
    )

    assert response.status_code == 200
    assert "complete range bounds" in response.get_data(as_text=True)


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
