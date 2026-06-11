from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class SpilloverInfo:
    """Parsed FCS spillover metadata."""

    keyword: str
    channels: list[str]
    matrix: np.ndarray
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "channels": self.channels,
            "matrix": self.matrix.tolist(),
            "warnings": self.warnings,
        }


def parse_spillover(keywords: dict[str, Any]) -> SpilloverInfo | None:
    """Parse $SPILL/$SPILLOVER-style metadata when present."""
    key, value = _find_spillover_keyword(keywords)
    if not key or value in (None, ""):
        return None
    try:
        from flowutils.compensate import get_spill

        matrix, channels = get_spill(str(value))
    except Exception as exc:
        return SpilloverInfo(
            keyword=key,
            channels=[],
            matrix=np.empty((0, 0)),
            warnings=[f"Spillover metadata was present but could not be parsed: {exc}"],
        )
    matrix = np.asarray(matrix, dtype=float)
    warnings = []
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        warnings.append("Spillover matrix is not square; conventional compensation was not applied.")
    if matrix.shape[0] != len(channels):
        warnings.append("Spillover matrix size does not match its channel labels.")
    return SpilloverInfo(keyword=key, channels=[str(channel) for channel in channels], matrix=matrix, warnings=warnings)


def apply_spillover_compensation(events: pd.DataFrame, spillover: SpilloverInfo | None) -> tuple[pd.DataFrame | None, list[str]]:
    """Apply FCS metadata compensation to matching fluorescence channels.

    Returns a new DataFrame and warnings. Raw events are never modified.
    """
    if spillover is None:
        return None, ["No spillover metadata found."]
    warnings = list(spillover.warnings)
    if warnings:
        return None, warnings
    resolved_channels, missing = _resolve_spillover_channels(events, spillover.channels)
    if missing:
        return None, [f"Spillover channels are missing from the event table: {', '.join(missing)}."]
    if spillover.matrix.shape != (len(spillover.channels), len(spillover.channels)):
        return None, ["Spillover matrix dimensions do not match channel labels."]
    try:
        from flowutils.compensate import compensate

        indices = [int(events.columns.get_loc(channel)) for channel in resolved_channels]
        compensated = compensate(events.to_numpy(dtype=float), spillover.matrix, fluoro_indices=indices)
    except Exception as exc:
        return None, [f"Could not apply spillover compensation: {exc}"]
    return pd.DataFrame(compensated, columns=events.columns, index=events.index), warnings


def event_view(sample, use_compensation: bool = False) -> pd.DataFrame:
    """Return raw or metadata-compensated events for display/statistics."""
    if use_compensation and getattr(sample, "compensated_events", None) is not None:
        return sample.compensated_events
    return sample.events


def compensation_status(sample) -> str:
    """Human-readable compensation state for the UI."""
    spillover = getattr(sample, "spillover", None)
    if spillover is None:
        return "No FCS spillover metadata detected. Showing raw exported values."
    if getattr(sample, "compensated_events", None) is not None:
        return f"Metadata compensation available from {spillover.keyword} for {len(spillover.channels)} channel(s)."
    warnings = getattr(sample, "compensation_warnings", [])
    if warnings:
        return "Compensation metadata detected, but not applied: " + " ".join(warnings)
    return "Compensation metadata detected, but not applied."


def _find_spillover_keyword(keywords: dict[str, Any]) -> tuple[str | None, Any]:
    for key, value in keywords.items():
        normalized = str(key).lower().strip().lstrip("$")
        if normalized in {"spill", "spillover"}:
            return str(key), value
    return None, None


def _resolve_spillover_channels(events: pd.DataFrame, channels: list[str]) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    missing: list[str] = []
    for channel in channels:
        if channel in events.columns:
            resolved.append(channel)
            continue
        if str(channel).isdigit():
            index = int(channel) - 1
            if 0 <= index < len(events.columns):
                resolved.append(str(events.columns[index]))
                continue
        missing.append(channel)
    return resolved, missing
