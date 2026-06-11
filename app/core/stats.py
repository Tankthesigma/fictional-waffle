from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.models.gate import GateDefinition


def gate_statistics(
    events: pd.DataFrame,
    gates: list[GateDefinition],
    masks: dict[str, np.ndarray],
    fluorescence_channels: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Compute counts, percentages, and fluorescence summaries for gates."""
    total_count = len(events)
    fluorescence_channels = fluorescence_channels or list(events.select_dtypes("number").columns)
    rows: list[dict[str, Any]] = []
    for gate in gates:
        mask = masks.get(gate.gate_id, np.zeros(total_count, dtype=bool))
        parent_count = total_count
        if gate.parent_id and gate.parent_id in masks:
            parent_count = int(np.sum(masks[gate.parent_id]))
        count = int(np.sum(mask))
        row: dict[str, Any] = {
            "gate_id": gate.gate_id,
            "gate_name": gate.name,
            "parent_gate": gate.parent_id or "total",
            "channels": ", ".join(gate.channels),
            "event_count": count,
            "percent_total": _pct(count, total_count),
            "percent_parent": _pct(count, parent_count),
        }
        gated = events.loc[mask]
        for channel in fluorescence_channels:
            if channel in gated.columns and len(gated):
                values = pd.to_numeric(gated[channel], errors="coerce")
                row[f"{channel}_median"] = float(values.median())
                row[f"{channel}_mean"] = float(values.mean())
                row[f"{channel}_p1"] = float(values.quantile(0.01))
                row[f"{channel}_p99"] = float(values.quantile(0.99))
            elif channel in events.columns:
                row[f"{channel}_median"] = None
                row[f"{channel}_mean"] = None
                row[f"{channel}_p1"] = None
                row[f"{channel}_p99"] = None
        rows.append(row)
    return rows


def fluorescence_medians(events: pd.DataFrame, fluorescence_channels: list[str]) -> dict[str, float | None]:
    """Compute fluorescence medians for a sample."""
    result: dict[str, float | None] = {}
    for channel in fluorescence_channels:
        if channel in events.columns:
            result[channel] = float(pd.to_numeric(events[channel], errors="coerce").median())
        else:
            result[channel] = None
    return result


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100.0, 3)
