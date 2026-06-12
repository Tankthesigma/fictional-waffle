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


def spillover_matrix_rows(sample) -> list[dict[str, Any]]:
    """Return an editable spillover matrix table for the current sample.

    The table uses fluorescence channels when no metadata matrix exists. Values
    are initialized to identity so a user can explicitly enter spillover terms.
    """
    spillover = getattr(sample, "spillover", None)
    if spillover is not None and spillover.channels and spillover.matrix.shape == (len(spillover.channels), len(spillover.channels)):
        channels = list(spillover.channels)
        matrix = np.asarray(spillover.matrix, dtype=float)
    else:
        channels = list(getattr(sample, "fluorescence_channels", []) or [])
        matrix = np.eye(len(channels), dtype=float)
    rows: list[dict[str, Any]] = []
    for row_index, channel in enumerate(channels):
        row: dict[str, Any] = {"channel": channel}
        for col_index, column_channel in enumerate(channels):
            row[column_channel] = float(matrix[row_index, col_index])
        rows.append(row)
    return rows


def spillover_from_matrix_rows(rows: list[dict[str, Any]], keyword: str = "manual") -> SpilloverInfo:
    """Build a SpilloverInfo object from editable matrix-table rows."""
    if not rows:
        raise ValueError("compensation matrix needs at least one channel")
    channels = [str(row.get("channel", "")).strip() for row in rows]
    if any(not channel for channel in channels):
        raise ValueError("every compensation matrix row needs a channel name")
    if len(set(channels)) != len(channels):
        raise ValueError("compensation matrix channel names must be unique")
    matrix = np.zeros((len(channels), len(channels)), dtype=float)
    for row_index, row in enumerate(rows):
        for col_index, channel in enumerate(channels):
            try:
                matrix[row_index, col_index] = float(row[channel])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"matrix value for {channels[row_index]} -> {channel} must be numeric") from exc
    warnings = _matrix_review_warnings(matrix)
    return SpilloverInfo(keyword=keyword, channels=channels, matrix=matrix, warnings=warnings)


def apply_manual_spillover(sample, rows: list[dict[str, Any]]) -> list[str]:
    """Apply a user-edited spillover matrix to a sample as a display/statistics view."""
    spillover = spillover_from_matrix_rows(rows, keyword="manual_editor")
    compensated, warnings = apply_spillover_compensation(sample.events, spillover)
    sample.spillover = spillover
    sample.compensated_events = compensated
    sample.compensation_warnings = warnings
    return warnings


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


def _matrix_review_warnings(matrix: np.ndarray) -> list[str]:
    warnings: list[str] = []
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        return ["Spillover matrix is not square; conventional compensation was not applied."]
    if matrix.size == 0:
        return ["Spillover matrix is empty."]
    diagonal = np.diag(matrix)
    if np.any(~np.isfinite(matrix)):
        warnings.append("Spillover matrix contains non-finite values.")
    if np.any(np.abs(diagonal) <= 1e-12):
        warnings.append("Spillover matrix has a near-zero diagonal value.")
    if np.linalg.cond(matrix) > 1e8:
        warnings.append("Spillover matrix is ill-conditioned; review before using compensated values.")
    return warnings
