from __future__ import annotations

from typing import Iterable

import pandas as pd

from app.core.downsample import downsample_events
from app.core.compensation import event_view
from app.core.transforms import apply_transform, log10_clamp_warning
from app.models.gate import GateDefinition
from app.models.sample import SampleRecord


def empty_figure(message: str = "Upload an FCS or event-level CSV file to begin."):
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_layout(template="plotly_white", height=560, margin=dict(l=40, r=20, t=40, b=40))
    return fig


def scatter_figure(
    sample: SampleRecord | None,
    x_channel: str | None,
    y_channel: str | None,
    *,
    plot_mode: str = "scatter",
    transform: str = "raw",
    cofactor: float = 150.0,
    max_events: int = 50_000,
    gates: Iterable[GateDefinition] | None = None,
    use_compensation: bool = False,
):
    """Build a Plotly cytometry scatter/density figure from a display downsample."""
    import plotly.graph_objects as go

    if sample is None or not x_channel or not y_channel:
        return empty_figure()
    events = event_view(sample, use_compensation)
    view_label = "metadata compensated events" if use_compensation and getattr(sample, "compensated_events", None) is not None else "raw events"
    if x_channel not in events or y_channel not in events:
        return empty_figure("Selected channels are not available for this sample.")
    display = downsample_events(events[[x_channel, y_channel]], max_events=max_events)
    display_transform, transform_warnings = _resolve_display_transform(sample, transform, use_compensation)
    transform_warnings.extend(_log10_warnings(events, [x_channel, y_channel], display_transform))
    try:
        x_values = apply_transform(display[x_channel], display_transform, cofactor=cofactor)
        y_values = apply_transform(display[y_channel], display_transform, cofactor=cofactor)
    except Exception as exc:
        return empty_figure(f"{display_transform} transform could not be displayed: {exc}")
    x_values, y_values = _finite_xy(x_values, y_values)
    if len(x_values) == 0:
        return empty_figure("Selected channels have no finite display values.")
    fig = go.Figure()
    normalized_mode = _normalize_plot_mode(plot_mode)
    if normalized_mode == "density":
        fig.add_trace(
            go.Histogram2d(
                x=x_values,
                y=y_values,
                nbinsx=160,
                nbinsy=160,
                colorscale="Viridis",
                colorbar=dict(title="Events/bin"),
                name=sample.sample_id,
                hovertemplate=f"{x_channel}: %{{x:.3g}}<br>{y_channel}: %{{y:.3g}}<br>Events: %{{z}}<extra></extra>",
            )
        )
    elif normalized_mode == "contour":
        fig.add_trace(
            go.Histogram2dContour(
                x=x_values,
                y=y_values,
                ncontours=18,
                colorscale="Viridis",
                contours=dict(coloring="heatmap"),
                line=dict(width=0.6, color="rgba(15,23,42,0.35)"),
                colorbar=dict(title="Density"),
                name=sample.sample_id,
                hovertemplate=f"{x_channel}: %{{x:.3g}}<br>{y_channel}: %{{y:.3g}}<br>Density: %{{z}}<extra></extra>",
            )
        )
    else:
        fig.add_trace(
            go.Scattergl(
                x=x_values,
                y=y_values,
                mode="markers",
                marker=dict(size=3, color="#2563eb", opacity=0.38),
                name=sample.sample_id,
            )
        )
    for gate in gates or []:
        if not gate.enabled or gate.gate_type != "rectangle" or gate.channels[:2] != [x_channel, y_channel]:
            continue
        gate_view = gate.metadata.get("event_view", "raw")
        current_view = "metadata_compensated" if use_compensation and getattr(sample, "compensated_events", None) is not None else "raw"
        if gate_view != current_view:
            continue
        _add_rectangle_shape(fig, gate, display_transform, cofactor)
    _add_transform_warnings(fig, transform_warnings)
    fig.update_layout(
        template="plotly_white",
        height=560,
        dragmode="zoom",
        margin=dict(l=50, r=24, t=42, b=50),
        title=f"{sample.sample_id}: {x_channel} vs {y_channel} ({view_label}, {display_transform} display, {_plot_mode_label(normalized_mode)})",
        xaxis_title=f"{x_channel} ({display_transform})",
        yaxis_title=f"{y_channel} ({display_transform})",
        hovermode="closest",
        uirevision=f"{sample.sample_id}:{x_channel}:{y_channel}:{display_transform}:{normalized_mode}",
    )
    return fig


def histogram_figure(
    samples: list[SampleRecord],
    channel: str | None,
    *,
    transform: str = "raw",
    cofactor: float = 150.0,
    max_events: int = 50_000,
    use_compensation: bool = False,
):
    """Build overlaid fluorescence histograms."""
    import plotly.graph_objects as go

    if not samples or not channel:
        return empty_figure("Select a fluorescence channel for histogram overlays.")
    fig = go.Figure()
    warnings: list[str] = []
    transforms_used: set[str] = set()
    for sample in samples:
        events = event_view(sample, use_compensation)
        if channel not in events:
            continue
        display_transform, transform_warnings = _resolve_display_transform(sample, transform, use_compensation)
        transforms_used.add(display_transform)
        warnings.extend(f"{sample.sample_id}: {warning}" for warning in transform_warnings)
        warnings.extend(f"{sample.sample_id}: {warning}" for warning in _log10_warnings(events, [channel], display_transform))
        display = downsample_events(pd.DataFrame({channel: events[channel]}), max_events=max_events)
        try:
            transformed = apply_transform(display[channel], display_transform, cofactor=cofactor)
        except Exception as exc:
            return empty_figure(f"{display_transform} transform could not be displayed: {exc}")
        fig.add_trace(
            go.Histogram(
                x=transformed,
                histnorm="probability density",
                opacity=0.55,
                name=sample.sample_id,
            )
        )
    _add_transform_warnings(fig, warnings)
    transform_label = next(iter(transforms_used)) if len(transforms_used) == 1 else (transform or "raw")
    fig.update_layout(
        template="plotly_white",
        barmode="overlay",
        height=420,
        margin=dict(l=50, r=24, t=42, b=50),
        title=f"{channel} histogram overlay ({'metadata compensated events' if use_compensation else 'raw events'}, {transform_label} display)",
        xaxis_title=f"{channel} ({transform_label})",
        yaxis_title="Density",
    )
    return fig


def event_count_chart(samples: list[SampleRecord]):
    import plotly.express as px

    if not samples:
        return empty_figure("Upload multiple samples to compare a batch.")
    frame = pd.DataFrame(
        {"sample_id": [s.sample_id for s in samples], "event_count": [s.event_count for s in samples], "condition": [s.condition or "" for s in samples]}
    )
    return px.bar(frame, x="sample_id", y="event_count", color="condition", template="plotly_white", title="Event counts")


def time_stability_figure(sample: SampleRecord | None):
    import plotly.express as px

    if sample is None:
        return empty_figure("Select a sample to inspect Time stability.")
    time_channel = sample.channel_by_role("time")
    if not time_channel or time_channel.raw_name not in sample.events:
        return empty_figure("No Time channel detected for this sample.")
    frame = pd.DataFrame({"Time": sample.events[time_channel.raw_name]})
    return px.histogram(frame, x="Time", nbins=40, template="plotly_white", title=f"{sample.sample_id}: event rate over Time")


def _add_rectangle_shape(fig, gate: GateDefinition, transform: str, cofactor: float) -> None:
    bounds = gate.bounds
    x0, x1 = apply_transform([bounds["x_min"], bounds["x_max"]], transform, cofactor=cofactor)
    y0, y1 = apply_transform([bounds["y_min"], bounds["y_max"]], transform, cofactor=cofactor)
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, line=dict(color="#0f766e", width=2), fillcolor="rgba(15,118,110,0.08)")
    fig.add_annotation(x=x1, y=y1, text=gate.name, showarrow=False, bgcolor="rgba(255,255,255,0.8)", font=dict(size=11, color="#0f172a"))


def _normalize_plot_mode(plot_mode: str | None) -> str:
    mode = (plot_mode or "scatter").strip().lower().replace("_", "-")
    if mode in {"density", "heatmap", "histogram2d", "histogram-2d"}:
        return "density"
    if mode in {"contour", "density-contour", "contours"}:
        return "contour"
    return "scatter"


def _plot_mode_label(plot_mode: str) -> str:
    if plot_mode == "density":
        return "density plot"
    if plot_mode == "contour":
        return "contour plot"
    return "dot plot"


def _resolve_display_transform(sample: SampleRecord, transform: str, use_compensation: bool) -> tuple[str, list[str]]:
    requested = transform or "raw"
    has_compensated_view = use_compensation and getattr(sample, "compensated_events", None) is not None
    if has_compensated_view and requested in {"log", "log10", "safe_log10"}:
        return (
            "arcsinh",
            [
                "Log10 display was switched to arcsinh for metadata-compensated values; "
                "compensated cytometry data can include real negative values."
            ],
        )
    return requested, []


def _log10_warnings(events: pd.DataFrame, channels: list[str], transform: str) -> list[str]:
    if transform not in {"log", "log10", "safe_log10"}:
        return []
    warnings: list[str] = []
    for channel in channels:
        if channel not in events:
            continue
        warning = log10_clamp_warning(channel, events[channel])
        if warning:
            warnings.append(warning)
    return warnings


def _add_transform_warnings(fig, warnings: list[str]) -> None:
    if not warnings:
        return
    text = "<br>".join(warnings[:3])
    if len(warnings) > 3:
        text += f"<br>+{len(warnings) - 3} more transform warning(s)"
    fig.add_annotation(
        text=text,
        showarrow=False,
        x=0,
        y=1.02,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="bottom",
        align="left",
        bgcolor="rgba(255,247,237,0.96)",
        bordercolor="#fed7aa",
        borderwidth=1,
        font=dict(size=11, color="#9a3412"),
    )


def _finite_xy(x_values, y_values):
    import numpy as np

    x_arr = np.asarray(x_values, dtype=float)
    y_arr = np.asarray(y_values, dtype=float)
    finite = np.isfinite(x_arr) & np.isfinite(y_arr)
    return x_arr[finite], y_arr[finite]
