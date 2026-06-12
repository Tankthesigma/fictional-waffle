from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.core.gate_colors import gate_color
from app.core.channel_inference import infer_channel_role
from app.models.gate import GateDefinition


def gate_statistics(
    events: pd.DataFrame,
    gates: list[GateDefinition],
    masks: dict[str, np.ndarray],
    fluorescence_channels: list[str] | None = None,
    channel_labels: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Compute counts, percentages, and fluorescence summaries for gates."""
    total_count = len(events)
    channel_labels = channel_labels or {}
    fluorescence_channels = fluorescence_channels or [
        column for column in events.select_dtypes("number").columns if infer_channel_role(str(column)) == "fluorescence"
    ]
    rows: list[dict[str, Any]] = []
    for gate in gates:
        mask = masks.get(gate.gate_id, np.zeros(total_count, dtype=bool))
        parent_count: int | None = total_count
        parent_label = "total"
        parent_missing = False
        if gate.parent_id and gate.parent_id in masks:
            parent_count = int(np.sum(masks[gate.parent_id]))
            parent_label = gate.parent_id
        elif gate.parent_id:
            parent_count = None
            parent_label = f"missing:{gate.parent_id}"
            parent_missing = True
        count = int(np.sum(mask))
        row: dict[str, Any] = {
            "gate_id": gate.gate_id,
            "gate_color": gate_color(gate.gate_id),
            "gate_name": gate.name,
            "parent_gate": parent_label,
            "parent_missing": parent_missing,
            "gate_warning": gate.metadata.get("mask_warning", ""),
            "channels": ", ".join(gate.channels),
            "channel_labels": ", ".join(channel_labels.get(channel, channel) for channel in gate.channels),
            "event_count": count,
            "percent_total": _pct(count, total_count),
            "percent_parent": _pct(count, parent_count) if parent_count is not None else None,
        }
        gated = events.loc[mask]
        for channel in fluorescence_channels:
            if channel in gated.columns and len(gated):
                values = pd.to_numeric(gated[channel], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
                summary = fluorescence_summary(values)
                row[f"{channel}_median"] = summary["median"]
                row[f"{channel}_mean"] = summary["mean"]
                row[f"{channel}_sd"] = summary["sd"]
                row[f"{channel}_cv_percent"] = summary["cv_percent"]
                row[f"{channel}_robust_cv_percent"] = summary["robust_cv_percent"]
                row[f"{channel}_geometric_mean"] = summary["geometric_mean"]
                row[f"{channel}_p1"] = summary["p1"]
                row[f"{channel}_p99"] = summary["p99"]
            elif channel in events.columns:
                row[f"{channel}_median"] = None
                row[f"{channel}_mean"] = None
                row[f"{channel}_sd"] = None
                row[f"{channel}_cv_percent"] = None
                row[f"{channel}_robust_cv_percent"] = None
                row[f"{channel}_geometric_mean"] = None
                row[f"{channel}_p1"] = None
                row[f"{channel}_p99"] = None
        rows.append(row)
    return rows


def fluorescence_summary(values: pd.Series) -> dict[str, float | None]:
    """Return common descriptive cytometry statistics for one numeric channel."""
    clean = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return {
            "median": None,
            "mean": None,
            "sd": None,
            "cv_percent": None,
            "robust_cv_percent": None,
            "geometric_mean": None,
            "p1": None,
            "p99": None,
        }
    median = float(clean.median())
    mean = float(clean.mean())
    sd = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
    mad = float((clean - median).abs().median())
    positive = clean[clean > 0]
    return {
        "median": median,
        "mean": mean,
        "sd": sd,
        "cv_percent": _ratio_percent(sd, mean),
        "robust_cv_percent": _ratio_percent(1.4826 * mad, median),
        "geometric_mean": float(np.exp(np.log(positive).mean())) if not positive.empty else None,
        "p1": float(clean.quantile(0.01)),
        "p99": float(clean.quantile(0.99)),
    }


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100.0, 3)


def _ratio_percent(numerator: float, denominator: float) -> float | None:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or abs(denominator) <= 1e-12:
        return None
    return float((numerator / denominator) * 100.0)
