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

    scatter_alias = _scatter_alias_role(norm)
    if scatter_alias:
        return scatter_alias
    if "fsc" in compact or "forwardscatter" in compact:
        return _geometry_role("fsc", norm)
    if "ssc" in compact or "sidescatter" in compact:
        return _geometry_role("ssc", norm)

    geometry_tokens = ("-a", "-h", "-w", "area", "height", "width")
    non_fluor_tokens = ("ratio", "pulse", "peak")
    if any(token in norm for token in geometry_tokens) and any(token in norm for token in non_fluor_tokens):
        return "unknown"

    if _looks_like_fluorescence(norm):
        return "fluorescence"
    if re.search(r"\d{3,4}[/\-]\d{2,4}", norm) or re.search(r"[a-z]+-\d{3,4}", norm):
        return "fluorescence"
    if display_label and display_label.strip() and _looks_like_detector_name(norm) and compact not in {"width", "height", "area"}:
        return "fluorescence"
    return "unknown"


def _looks_like_fluorescence(norm: str) -> bool:
    tokens = [token for token in re.split(r"[^a-z0-9+]+", norm) if token]
    exact_tokens = {"fitc", "pe", "apc", "percp", "pacific", "alexafluor", "fl", "cy"}
    if any(token in exact_tokens for token in tokens):
        return True
    prefixes = ("fl", "bv", "af", "cy")
    return any(re.fullmatch(rf"{prefix}\d+[a-z0-9]*", token) for prefix in prefixes for token in tokens)


def _looks_like_detector_name(norm: str) -> bool:
    compact = norm.replace("-", "")
    return bool(
        re.search(r"(^|-)fl\d+", norm)
        or re.search(r"\d{3,4}[/\-]\d{2,4}", norm)
        or re.fullmatch(r"[a-z]{1,3}\d{1,2}[-/]?[ahw]?", compact)
    )


def _scatter_alias_role(norm: str) -> str | None:
    """Recognize common exported FS/SS scatter aliases without overmatching."""
    tokens = [token for token in re.split(r"[^a-z0-9]+", norm) if token]
    if not tokens:
        return None
    token_set = set(tokens)
    if token_set <= {"fs", "lin", "linear", "log", "logarithmic"} and "fs" in token_set:
        return _geometry_role("fsc", norm)
    if token_set <= {"ss", "lin", "linear", "log", "logarithmic"} and "ss" in token_set:
        return _geometry_role("ssc", norm)
    if tokens[:2] == ["forward", "scatter"]:
        return _geometry_role("fsc", norm)
    if tokens[:2] == ["side", "scatter"]:
        return _geometry_role("ssc", norm)
    return None


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
    value = _lookup_pn_value(metadata, index, "s")
    if value:
        return str(value)
    return None


def _lookup_range(metadata: dict[str, Any], index: int) -> float | None:
    value = _lookup_pn_value(metadata, index, "r")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _lookup_channel_metadata(metadata: dict[str, Any], index: int) -> dict[str, Any]:
    channel_meta: dict[str, Any] = {}
    for key, value in metadata.items():
        parsed = _parse_pn_keyword(str(key))
        if parsed and parsed[0] == index:
            channel_meta[str(key)] = value
    return channel_meta


def _lookup_pn_value(metadata: dict[str, Any], index: int, suffix: str) -> Any:
    suffix = suffix.lower()
    for key, value in metadata.items():
        parsed = _parse_pn_keyword(str(key))
        if parsed and parsed == (index, suffix):
            return value
    return None


def _parse_pn_keyword(key: str) -> tuple[int, str] | None:
    match = re.fullmatch(r"\$?p(\d+)([a-z].*)", key.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1)), match.group(2).lower()
