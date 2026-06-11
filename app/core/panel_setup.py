from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.channel_inference import infer_channel_role
from app.models.channel import ChannelSummary
from app.models.sample import SampleRecord


PANEL_KEY_COLUMNS = ("channel", "raw_name", "pnn", "detector")
PANEL_VALUE_COLUMNS = ("display_label", "marker", "antibody", "fluorochrome", "role")
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


def _normalize_column(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_key(value: Any) -> str:
    return str(value).strip().lower()
