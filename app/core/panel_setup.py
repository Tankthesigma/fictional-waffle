from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.channel_inference import infer_channel_role
from app.models.channel import ChannelSummary
from app.models.sample import SampleRecord


PANEL_KEY_COLUMNS = ("channel", "raw_name", "pnn", "detector")
PANEL_VALUE_COLUMNS = ("display_label", "marker", "antibody", "fluorochrome", "role")
PANEL_TEMPLATE_COLUMNS = ["channel", "display_label", "marker", "antibody", "fluorochrome", "role"]
SUPPORTED_PANEL_ROLES = {
    "fsc",
    "fsc-a",
    "fsc-h",
    "fsc-w",
    "ssc",
    "ssc-a",
    "ssc-h",
    "ssc-w",
    "time",
    "fluorescence",
    "index",
    "unknown",
}


def parse_panel_setup(path: str | Path) -> dict[str, dict[str, str]]:
    """Parse an optional channel/antibody setup CSV keyed by detector name."""
    data = pd.read_csv(path, dtype=str).fillna("")
    normalized = {_normalize_column(column): column for column in data.columns}
    key_column = next((normalized[name] for name in PANEL_KEY_COLUMNS if name in normalized), None)
    if key_column is None:
        raise ValueError("panel setup missing a channel key column: channel, raw_name, pnn, or detector")
    rows: dict[str, dict[str, str]] = {}
    for _, row in data.iterrows():
        key = str(row.get(key_column, "")).strip()
        if not key:
            continue
        normalized_key = _normalize_key(key)
        if normalized_key in rows:
            raise ValueError(f"panel setup contains duplicate channel key: {key}")
        payload: dict[str, str] = {"channel": key}
        for field in PANEL_VALUE_COLUMNS:
            source = normalized.get(field)
            if source:
                value = str(row.get(source, "")).strip()
                if value:
                    payload[field] = value
        rows[normalized_key] = payload
    return rows


def apply_panel_setup(samples: list[SampleRecord], panel: dict[str, dict[str, str]]) -> list[str]:
    """Apply marker, antibody, fluorochrome, and role metadata to samples."""
    warnings: list[str] = []
    if not panel:
        return warnings
    for sample in samples:
        matched = 0
        for channel in sample.channels:
            item = _match_panel_row(channel, panel)
            if item is None:
                continue
            matched += 1
            _apply_row(channel, item)
        if matched == 0:
            warnings.append(f"{sample.filename}: panel setup did not match any channels.")
    return warnings


def panel_readiness_summary(sample: SampleRecord | None) -> dict[str, int | str]:
    """Summarize whether a selected sample has useful channel/panel labels."""
    if sample is None:
        return {
            "total_channels": 0,
            "fluorescence_channels": 0,
            "labeled_fluorescence": 0,
            "unlabeled_fluorescence": 0,
            "unknown_channels": 0,
            "status": "waiting",
        }
    fluorescence = [channel for channel in sample.channels if channel.role == "fluorescence"]
    labeled = [channel for channel in fluorescence if _has_panel_label(channel)]
    unknown = [channel for channel in sample.channels if channel.role == "unknown"]
    status = "ready"
    if unknown:
        status = "review roles"
    if fluorescence and len(labeled) < len(fluorescence):
        status = "label antibodies"
    if not fluorescence:
        status = "review channels"
    return {
        "total_channels": len(sample.channels),
        "fluorescence_channels": len(fluorescence),
        "labeled_fluorescence": len(labeled),
        "unlabeled_fluorescence": len(fluorescence) - len(labeled),
        "unknown_channels": len(unknown),
        "status": status,
    }


def panel_readiness_rows(sample: SampleRecord | None) -> list[dict[str, str]]:
    """Return display rows that make channel setup gaps visible in the UI."""
    if sample is None:
        return []
    rows = []
    for channel in sample.channels:
        rows.append(
            {
                "channel": channel.raw_name,
                "display_label": channel.display_label or "",
                "marker": channel.marker or "",
                "antibody": channel.antibody or "",
                "fluorochrome": channel.fluorochrome or "",
                "role": channel.role,
                "status": _readiness_status(channel),
                "next_step": _readiness_next_step(channel),
            }
        )
    return rows


def panel_template_rows(sample: SampleRecord | None = None) -> list[dict[str, str]]:
    """Build CSV-ready panel setup rows for a selected sample or generic example."""
    if sample is None or not sample.channels:
        return [
            {
                "channel": "FL1-A",
                "display_label": "FITC detector",
                "marker": "CD3",
                "antibody": "UCHT1",
                "fluorochrome": "FITC",
                "role": "fluorescence",
            },
            {
                "channel": "FL2-A",
                "display_label": "PE detector",
                "marker": "CD19",
                "antibody": "HIB19",
                "fluorochrome": "PE",
                "role": "fluorescence",
            },
        ]
    return [
        {
            "channel": channel.raw_name,
            "display_label": channel.display_label or "",
            "marker": channel.marker or "",
            "antibody": channel.antibody or "",
            "fluorochrome": channel.fluorochrome or "",
            "role": channel.role,
        }
        for channel in sample.channels
    ]


def _match_panel_row(channel: ChannelSummary, panel: dict[str, dict[str, str]]) -> dict[str, str] | None:
    for key in [channel.raw_name, channel.display_label or "", channel.marker or "", channel.fluorochrome or ""]:
        item = panel.get(_normalize_key(key))
        if item is not None:
            return item
    return None


def _apply_row(channel: ChannelSummary, item: dict[str, str]) -> None:
    channel.display_label = item.get("display_label") or channel.display_label
    channel.marker = item.get("marker") or channel.marker
    channel.antibody = item.get("antibody") or channel.antibody
    channel.fluorochrome = item.get("fluorochrome") or channel.fluorochrome
    role = (item.get("role") or "").strip().lower().replace("_", "-")
    if role:
        channel.role = role if role in SUPPORTED_PANEL_ROLES else infer_channel_role(channel.raw_name, role)


def _has_panel_label(channel: ChannelSummary) -> bool:
    return bool(channel.marker or channel.antibody or channel.fluorochrome)


def _readiness_status(channel: ChannelSummary) -> str:
    if channel.role == "unknown":
        return "review role"
    if channel.role == "fluorescence" and not _has_panel_label(channel):
        return "needs label"
    if channel.role == "fluorescence":
        return "labeled"
    return "instrument/context"


def _readiness_next_step(channel: ChannelSummary) -> str:
    if channel.role == "unknown":
        return "Confirm detector role before gating or comparison."
    if channel.role == "fluorescence" and not _has_panel_label(channel):
        return "Add marker, antibody, or fluorochrome in a panel setup CSV."
    if channel.role == "fluorescence":
        return "Ready for marker-aware plots, gates, and reports."
    return "Keep inferred role unless metadata suggests otherwise."


def _normalize_column(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_key(value: Any) -> str:
    return str(value).strip().lower()
