from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from app.models.channel import ChannelSummary


ROLE_ORDER = [
    "fsc-a",
    "ssc-a",
    "fsc",
    "ssc",
    "time",
    "fluorescence",
    "index",
    "unknown",
]


def normalize_channel_name(name: str | None) -> str:
    """Normalize channel names for fuzzy role inference."""
    if not name:
        return ""
    text = name.lower().strip()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9+\-/]", "", text)
    return text


def infer_channel_role(raw_name: str, display_label: str | None = None) -> str:
    """Infer a cytometry channel role from PnN/PnS-style names.

    The rules intentionally avoid instrument-specific channel maps. They only
    inspect text patterns commonly present in exported FCS metadata.
    """
    combined = " ".join(filter(None, [raw_name, display_label]))
    norm = normalize_channel_name(combined)
    compact = norm.replace("-", "")

    if not norm:
        return "unknown"
    if "time" in compact:
        return "time"
    if compact in {"event", "events", "eventnumber", "index"} or "eventnumber" in compact:
        return "index"

    if "fsc" in compact or "forwardscatter" in compact:
        return _geometry_role("fsc", norm)
    if "ssc" in compact or "sidescatter" in compact:
        return _geometry_role("ssc", norm)

    geometry_tokens = ("-a", "-h", "-w", "area", "height", "width")
    non_fluor_tokens = ("ratio", "pulse", "peak")
    if any(token in norm for token in geometry_tokens) and any(token in norm for token in non_fluor_tokens):
        return "unknown"

    if any(token in norm for token in ("fl", "fitc", "pe", "apc", "percp", "pacific", "alexafluor", "bv", "cy", "af")):
        return "fluorescence"
    if re.search(r"\d{3,4}[/\-]\d{2,4}", norm) or re.search(r"[a-z]+-\d{3,4}", norm):
        return "fluorescence"
    if display_label and display_label.strip() and compact not in {"width", "height", "area"}:
        return "fluorescence"
    return "unknown"


def _geometry_role(prefix: str, norm: str) -> str:
    if re.search(r"(^|[-/])a($|[-/])", norm) or "area" in norm:
        return f"{prefix}-a"
    if re.search(r"(^|[-/])h($|[-/])", norm) or "height" in norm:
        return f"{prefix}-h"
    if re.search(r"(^|[-/])w($|[-/])", norm) or "width" in norm:
        return f"{prefix}-w"
    return prefix


def summarize_channels(
    events: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
    role_overrides: dict[str, str] | None = None,
) -> list[ChannelSummary]:
    """Create per-channel metadata summaries from an event matrix."""
    metadata = metadata or {}
    role_overrides = role_overrides or {}
    summaries: list[ChannelSummary] = []
    for index, column in enumerate(events.columns, start=1):
        raw_name = str(column)
        display_label = _lookup_display_label(metadata, index)
        values = pd.to_numeric(events[column], errors="coerce").to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        summary = ChannelSummary(
            index=index,
            raw_name=raw_name,
            display_label=display_label,
            role=role_overrides.get(raw_name) or infer_channel_role(raw_name, display_label),
            metadata=_lookup_channel_metadata(metadata, index),
        )
        if finite.size:
            percentiles = np.nanpercentile(finite, [1, 5, 50, 95, 99])
            summary.minimum = float(np.nanmin(finite))
            summary.maximum = float(np.nanmax(finite))
            summary.p1, summary.p5, summary.median, summary.p95, summary.p99 = map(float, percentiles)
            summary.range_value = _lookup_range(metadata, index)
            span = summary.maximum - summary.minimum
            tolerance = max(span * 0.001, 1e-9)
            summary.percent_near_min = float(np.mean(finite <= summary.minimum + tolerance) * 100.0)
            summary.percent_near_max = float(np.mean(finite >= summary.maximum - tolerance) * 100.0)
            if summary.percent_near_max >= 1.0:
                summary.notes.append("possible high-end clipping")
            if summary.percent_near_min >= 1.0:
                summary.notes.append("possible low-end clipping")
        else:
            summary.notes.append("no numeric values")
        summaries.append(summary)
    return summaries


def best_scatter_pair(channels: list[ChannelSummary]) -> tuple[str | None, str | None]:
    """Pick the best default FSC/SSC pair from inferred channel roles."""
    fsc = _best_role(channels, ["fsc-a", "fsc", "fsc-h", "fsc-w"])
    ssc = _best_role(channels, ["ssc-a", "ssc", "ssc-h", "ssc-w"])
    return (fsc.raw_name if fsc else None, ssc.raw_name if ssc else None)


def _best_role(channels: list[ChannelSummary], roles: list[str]) -> ChannelSummary | None:
    for role in roles:
        for channel in channels:
            if channel.role == role:
                return channel
    return None


def _lookup_display_label(metadata: dict[str, Any], index: int) -> str | None:
    for key in (f"p{index}s", f"$p{index}s", f"P{index}S", f"$P{index}S"):
        if key in metadata and metadata[key]:
            return str(metadata[key])
    return None


def _lookup_range(metadata: dict[str, Any], index: int) -> float | None:
    for key in (f"p{index}r", f"$p{index}r", f"P{index}R", f"$P{index}R"):
        if key in metadata:
            try:
                return float(metadata[key])
            except (TypeError, ValueError):
                return None
    return None


def _lookup_channel_metadata(metadata: dict[str, Any], index: int) -> dict[str, Any]:
    channel_meta: dict[str, Any] = {}
    patterns = (f"p{index}", f"$p{index}", f"P{index}", f"$P{index}")
    for key, value in metadata.items():
        if any(str(key).startswith(pattern) for pattern in patterns):
            channel_meta[str(key)] = value
    return channel_meta
