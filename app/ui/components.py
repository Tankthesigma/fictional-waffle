from __future__ import annotations

from dash import dash_table, dcc, html


def card(title: str, children, class_name: str = ""):
    body = children if isinstance(children, list) else [children]
    return html.Section([html.H3(title), *body], className=f"card {class_name}".strip())


def upload_box(component_id: str, label: str, multiple: bool = True):
    return dcc.Upload(
        id=component_id,
        children=html.Div([html.Strong(label), html.Span(" Drag files here or click to choose.")]),
        multiple=multiple,
        className="upload-box",
    )


def data_table(component_id: str, columns: list[str], **kwargs):
    page_size = kwargs.pop("page_size", 10)
    return dash_table.DataTable(
        id=component_id,
        columns=[{"name": column.replace("_", " ").title(), "id": column} for column in columns],
        data=[],
        page_size=page_size,
        filter_action="native",
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "Inter, system-ui, sans-serif", "fontSize": 13, "padding": "8px", "textAlign": "left"},
        style_header={"fontWeight": 700, "backgroundColor": "#f8fafc"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#fbfdff"},
            {"if": {"filter_query": "{severity} = severe"}, "backgroundColor": "#fee2e2"},
            {"if": {"filter_query": "{severity} = warning"}, "backgroundColor": "#fef3c7"},
        ],
        **kwargs,
    )


def table_columns(columns: list[str]):
    return [{"name": column.replace("_", " ").title(), "id": column} for column in columns]


def metric_card(label: str, value_id: str, tone: str = ""):
    return html.Div([html.Span(label), html.Strong(id=value_id)], className=f"metric {tone}".strip())
