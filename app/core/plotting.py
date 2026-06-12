from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

from app.core.downsample import downsample_events
from app.core.compensation import event_view
from app.core.gate_colors import gate_color
from app.core.transforms import apply_transform, log10_clamp_warning
from app.core.transform_settings import resolve_channel_transform
from app.models.gate import GateDefinition
from app.models.sample import SampleRecord

logger = logging.getLogger(__name__)


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
    channel_transform_overrides: dict | None = None,
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
    x_setting = resolve_channel_transform(x_channel, transform, cofactor, channel_transform_overrides)
    y_setting = resolve_channel_transform(y_channel, transform, cofactor, channel_transform_overrides)
    x_transform, x_warnings = _resolve_display_transform(sample, x_setting.transform, use_compensation)
    y_transform, y_warnings = _resolve_display_transform(sample, y_setting.transform, use_compensation)
    transform_warnings = [*x_warnings, *y_warnings]
    transform_warnings.extend(_log10_warnings(events, [x_channel], x_transform))
    transform_warnings.extend(_log10_warnings(events, [y_channel], y_transform))
    try:
        x_values = apply_transform(display[x_channel], x_transform, cofactor=x_setting.cofactor)
        y_values = apply_transform(display[y_channel], y_transform, cofactor=y_setting.cofactor)
    except Exception as exc:
        logger.exception("Scatter transform failed for %s on %s/%s", sample.sample_id, x_channel, y_channel)
        return empty_figure(f"{_display_label(x_transform, y_transform)} transform could not be displayed: {exc}")
    x_values, y_values = _finite_xy(x_values, y_values)
    if len(x_values) == 0:
        return empty_figure("Selected channels have no finite display values.")
    x_range = _display_range(x_values)
    y_range = _display_range(y_values)
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
                hovertemplate=f"{_channel_label(sample, x_channel)}: %{{x:.3g}}<br>{_channel_label(sample, y_channel)}: %{{y:.3g}}<br>Events: %{{z}}<extra></extra>",
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
                hovertemplate=f"{_channel_label(sample, x_channel)}: %{{x:.3g}}<br>{_channel_label(sample, y_channel)}: %{{y:.3g}}<br>Density: %{{z}}<extra></extra>",
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
        if not gate.enabled or gate.channels[:2] != [x_channel, y_channel]:
            continue
        gate_view = gate.metadata.get("event_view", "raw")
        current_view = "metadata_compensated" if use_compensation and getattr(sample, "compensated_events", None) is not None else "raw"
        if gate_view != current_view:
            continue
        if gate.gate_type in {"rectangle", "bi_range"}:
            _add_rectangle_shape(fig, gate, x_transform, x_setting.cofactor, y_transform, y_setting.cofactor)
        elif gate.gate_type == "polygon":
            _add_polygon_shape(fig, gate, x_transform, x_setting.cofactor, y_transform, y_setting.cofactor)
        elif gate.gate_type == "ellipse":
            _add_ellipse_shape(fig, gate, x_transform, x_setting.cofactor, y_transform, y_setting.cofactor)
        elif gate.gate_type == "quadrant":
            _add_quadrant_shape(fig, gate, x_transform, x_setting.cofactor, y_transform, y_setting.cofactor)
    _add_transform_warnings(fig, transform_warnings)
    layout = dict(
        template="plotly_white",
        height=560,
        dragmode="zoom",
        margin=dict(l=50, r=24, t=42, b=50),
        title=f"{sample.sample_id}: {_channel_label(sample, x_channel)} vs {_channel_label(sample, y_channel)} ({view_label}, {_display_label(x_transform, y_transform)} display, {_plot_mode_label(normalized_mode)})",
        xaxis_title=f"{_channel_label(sample, x_channel)} ({x_transform})",
        yaxis_title=f"{_channel_label(sample, y_channel)} ({y_transform})",
        hovermode="closest",
        uirevision=f"{sample.sample_id}:{x_channel}:{y_channel}:{x_transform}:{y_transform}:{normalized_mode}",
    )
    if x_range:
        layout["xaxis"] = dict(range=x_range)
    if y_range:
        layout["yaxis"] = dict(range=y_range)
    fig.update_layout(**layout)
    return fig


def histogram_figure(
    samples: list[SampleRecord],
    channel: str | None,
    *,
    transform: str = "raw",
    cofactor: float = 150.0,
    max_events: int = 50_000,
    use_compensation: bool = False,
    channel_transform_overrides: dict | None = None,
):
    """Build overlaid fluorescence histograms."""
    import plotly.graph_objects as go

    if not samples or not channel:
        return empty_figure("Select a fluorescence channel for histogram overlays.")
    fig = go.Figure()
    warnings: list[str] = []
    transforms_used: set[str] = set()
    histogram_values = []
    for sample in samples:
        events = event_view(sample, use_compensation)
        if channel not in events:
            continue
        setting = resolve_channel_transform(channel, transform, cofactor, channel_transform_overrides)
        display_transform, transform_warnings = _resolve_display_transform(sample, setting.transform, use_compensation)
        transforms_used.add(display_transform)
        warnings.extend(f"{sample.sample_id}: {warning}" for warning in transform_warnings)
        warnings.extend(f"{sample.sample_id}: {warning}" for warning in _log10_warnings(events, [channel], display_transform))
        display = downsample_events(pd.DataFrame({channel: events[channel]}), max_events=max_events)
        try:
            transformed = apply_transform(display[channel], display_transform, cofactor=setting.cofactor)
        except Exception as exc:
            logger.exception("Histogram transform failed for %s on %s", sample.sample_id, channel)
            return empty_figure(f"{display_transform} transform could not be displayed: {exc}")
        fig.add_trace(
            go.Histogram(
                x=transformed,
                histnorm="probability density",
                opacity=0.55,
                name=sample.sample_id,
            )
        )
        histogram_values.extend(_finite_values(transformed))
    _add_transform_warnings(fig, warnings)
    transform_label = next(iter(transforms_used)) if len(transforms_used) == 1 else (transform or "raw")
    layout = dict(
        template="plotly_white",
        barmode="overlay",
        height=420,
        margin=dict(l=50, r=24, t=42, b=50),
        title=f"{_channel_label(samples[0], channel)} histogram overlay ({'metadata compensated events' if use_compensation else 'raw events'}, {transform_label} display)",
        xaxis_title=f"{_channel_label(samples[0], channel)} ({transform_label})",
        yaxis_title="Density",
    )
    histogram_range = _display_range(histogram_values)
    if histogram_range:
        layout["xaxis"] = dict(range=histogram_range)
    fig.update_layout(**layout)
    return fig


def event_count_chart(samples: list[SampleRecord]):
    import plotly.express as px

    if not samples:
        return empty_figure("Upload multiple samples to compare a batch.")
    frame = pd.DataFrame(
        {"sample_id": [s.sample_id for s in samples], "event_count": [s.event_count for s in samples], "condition": [s.condition or "" for s in samples]}
    )
    return px.bar(frame, x="sample_id", y="event_count", color="condition", template="plotly_white", title="Event counts")


def comparison_delta_chart(rows: list[dict[str, object]]):
    """Build an exploratory control-versus-treated median-difference chart."""
    import plotly.graph_objects as go

    numeric_rows = []
    for row in rows:
        diff = _number_or_none(row.get("median_difference"))
        if diff is None:
            continue
        label = str(row.get("channel_label") or row.get("channel", "channel"))
        raw_channel = str(row.get("channel", label))
        numeric_rows.append((label, raw_channel, diff, str(row.get("notes", ""))))
    if not numeric_rows:
        return empty_figure("Choose control and treated groups to plot exploratory median differences.")

    numeric_rows.sort(key=lambda item: abs(item[2]), reverse=True)
    channels = [item[0] for item in numeric_rows[:24]]
    raw_channels = [item[1] for item in numeric_rows[:24]]
    differences = [item[2] for item in numeric_rows[:24]]
    notes = [item[3] for item in numeric_rows[:24]]
    colors = ["#0f766e" if value >= 0 else "#b45309" for value in differences]
    guarded = sum("fold-change not computed" in note for note in notes)
    low_replicate = sum("replicate count is too low" in note for note in notes)

    fig = go.Figure(
        go.Bar(
            x=differences,
            y=channels,
            orientation="h",
            marker=dict(color=colors),
            customdata=list(zip(raw_channels, notes, strict=False)),
            hovertemplate="Channel: %{y}<br>Raw detector: %{customdata[0]}<br>Median difference: %{x:.3g}<br>%{customdata[1]}<extra></extra>",
        )
    )
    fig.add_vline(x=0, line_color="#94a3b8", line_width=1)
    fig.update_layout(
        template="plotly_white",
        height=max(360, min(680, 120 + len(channels) * 32)),
        margin=dict(l=90, r=30, t=58, b=48),
        title="Exploratory control-vs-treated median differences",
        xaxis_title="Treated median - control median",
        yaxis_title="Fluorescence channel",
        yaxis=dict(autorange="reversed"),
        annotations=[
            dict(
                text=f"Descriptive only | guarded fold-change rows: {guarded} | low-replicate rows: {low_replicate}",
                x=0,
                y=1.08,
                xref="paper",
                yref="paper",
                showarrow=False,
                xanchor="left",
                font=dict(size=12, color="#64748b"),
            )
        ],
    )
    return fig


def time_stability_figure(sample: SampleRecord | None):
    import plotly.express as px

    if sample is None:
        return empty_figure("Select a sample to inspect Time stability.")
    time_channel = sample.channel_by_role("time")
    if not time_channel or time_channel.raw_name not in sample.events:
        return empty_figure("No Time channel detected for this sample.")
    frame = pd.DataFrame({"Time": sample.events[time_channel.raw_name]})
    return px.histogram(frame, x="Time", nbins=40, template="plotly_white", title=f"{sample.sample_id}: event rate over Time")


def high_dimensional_cluster_figure_from_review(review, *, sample_id: str = "sample"):
    """Render a precomputed high-dimensional review result."""
    import plotly.express as px

    if review.embedding.empty:
        message = review.warnings[0] if review.warnings else "High-dimensional review is unavailable for this sample."
        return empty_figure(message)
    frame = review.embedding.copy()
    frame["cluster"] = frame["cluster"].astype(str)
    fig = px.scatter(
        frame,
        x="dim1",
        y="dim2",
        color="cluster",
        render_mode="webgl",
        template="plotly_white",
        title=f"{sample_id}: {review.reducer.upper()} cluster review",
        labels={"dim1": f"{review.reducer.upper()} 1", "dim2": f"{review.reducer.upper()} 2", "cluster": "Cluster"},
    )
    fig.update_traces(marker=dict(size=4, opacity=0.62), hovertemplate="Cluster %{marker.color}<br>%{x:.3g}, %{y:.3g}<extra></extra>")
    fig.update_layout(height=460, margin=dict(l=50, r=24, t=54, b=50))
    _add_transform_warnings(fig, review.warnings)
    return fig


def _add_rectangle_shape(fig, gate: GateDefinition, x_transform: str, x_cofactor: float, y_transform: str, y_cofactor: float) -> None:
    bounds = gate.bounds
    x0, x1 = apply_transform([bounds["x_min"], bounds["x_max"]], x_transform, cofactor=x_cofactor)
    y0, y1 = apply_transform([bounds["y_min"], bounds["y_max"]], y_transform, cofactor=y_cofactor)
    color = gate_color(gate.gate_id)
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, line=dict(color=color, width=2), fillcolor=_hex_rgba(color, 0.08))
    fig.add_annotation(x=x1, y=y1, text=gate.name, showarrow=False, bgcolor="rgba(255,255,255,0.8)", font=dict(size=11, color=color))


def _add_polygon_shape(fig, gate: GateDefinition, x_transform: str, x_cofactor: float, y_transform: str, y_cofactor: float) -> None:
    if len(gate.vertices) < 3:
        return
    x_values, y_values = zip(*gate.vertices, strict=False)
    x_display = apply_transform(x_values, x_transform, cofactor=x_cofactor)
    y_display = apply_transform(y_values, y_transform, cofactor=y_cofactor)
    path_parts = [f"M {x_display[0]},{y_display[0]}"]
    path_parts.extend(f"L {x},{y}" for x, y in zip(x_display[1:], y_display[1:], strict=False))
    path_parts.append("Z")
    color = gate_color(gate.gate_id)
    fig.add_shape(
        type="path",
        path=" ".join(path_parts),
        line=dict(color=color, width=2),
        fillcolor=_hex_rgba(color, 0.08),
    )
    fig.add_annotation(
        x=float(x_display[-1]),
        y=float(y_display[-1]),
        text=gate.name,
        showarrow=False,
        bgcolor="rgba(255,255,255,0.8)",
        font=dict(size=11, color=color),
    )


def _add_ellipse_shape(fig, gate: GateDefinition, x_transform: str, x_cofactor: float, y_transform: str, y_cofactor: float) -> None:
    bounds = gate.bounds
    center_x = float(bounds["center_x"])
    center_y = float(bounds["center_y"])
    radius_x = float(bounds["radius_x"])
    radius_y = float(bounds["radius_y"])
    x0, x1 = apply_transform([center_x - radius_x, center_x + radius_x], x_transform, cofactor=x_cofactor)
    y0, y1 = apply_transform([center_y - radius_y, center_y + radius_y], y_transform, cofactor=y_cofactor)
    color = gate_color(gate.gate_id)
    fig.add_shape(type="circle", x0=x0, x1=x1, y0=y0, y1=y1, line=dict(color=color, width=2), fillcolor=_hex_rgba(color, 0.08))
    fig.add_annotation(x=x1, y=y1, text=gate.name, showarrow=False, bgcolor="rgba(255,255,255,0.8)", font=dict(size=11, color=color))


def _add_quadrant_shape(fig, gate: GateDefinition, x_transform: str, x_cofactor: float, y_transform: str, y_cofactor: float) -> None:
    bounds = gate.bounds
    x_threshold = float(apply_transform([bounds["x_threshold"]], x_transform, cofactor=x_cofactor)[0])
    y_threshold = float(apply_transform([bounds["y_threshold"]], y_transform, cofactor=y_cofactor)[0])
    color = gate_color(gate.gate_id)
    fig.add_vline(x=x_threshold, line_color=color, line_width=1.7, line_dash="dash")
    fig.add_hline(y=y_threshold, line_color=color, line_width=1.7, line_dash="dash")
    fig.add_annotation(
        x=x_threshold,
        y=y_threshold,
        text="Quadrants",
        showarrow=False,
        bgcolor="rgba(255,255,255,0.82)",
        font=dict(size=11, color=color),
    )


def _hex_rgba(color: str, alpha: float) -> str:
    value = color.lstrip("#")
    if len(value) != 6:
        return f"rgba(15,118,110,{alpha})"
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red},{green},{blue},{alpha})"


def _channel_label(sample: SampleRecord, raw_name: str) -> str:
    for channel in sample.channels:
        if channel.raw_name == raw_name:
            return channel.label
    return raw_name


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


def _display_label(x_transform: str, y_transform: str) -> str:
    if x_transform == y_transform:
        return x_transform
    return f"x={x_transform}, y={y_transform}"


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


def _finite_values(values) -> list[float]:
    import numpy as np

    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)].tolist()


def _display_range(values) -> list[float] | None:
    import numpy as np

    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return None
    if len(arr) >= 20:
        low, high = np.percentile(arr, [0.1, 99.9])
    else:
        low, high = float(np.min(arr)), float(np.max(arr))
    if not np.isfinite(low) or not np.isfinite(high):
        return None
    if low == high:
        pad = abs(low) * 0.05 or 1.0
        return [float(low - pad), float(high + pad)]
    pad = (high - low) * 0.04
    return [float(low - pad), float(high + pad)]


def _number_or_none(value: object) -> float | None:
    import numpy as np

    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None
