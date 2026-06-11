from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from app.core.compensation import event_view
from app.models.comparison import ComparisonResult
from app.models.sample import SampleRecord


def batch_table(samples: list[SampleRecord]) -> list[dict[str, object]]:
    """Return a compact table for batch overview."""
    return [
        {
            "sample_id": sample.sample_id,
            "condition": sample.condition or "",
            "replicate": sample.replicate or "",
            "control_type": sample.control_type or "",
            "event_count": sample.event_count,
            "fluorescence_channels": len(sample.fluorescence_channels),
            "file_type": sample.file_type,
        }
        for sample in samples
    ]


def fluorescence_median_table(samples: list[SampleRecord], use_compensation: bool = False) -> list[dict[str, object]]:
    """Compute a fluorescence median table across samples."""
    channels = sorted({channel for sample in samples for channel in sample.fluorescence_channels})
    rows: list[dict[str, object]] = []
    for sample in samples:
        row: dict[str, object] = {"sample_id": sample.sample_id, "condition": sample.condition or ""}
        events = event_view(sample, use_compensation)
        for channel in channels:
            if channel in events:
                row[channel] = _series_median_or_none(events[channel])
            else:
                row[channel] = None
        rows.append(row)
    return rows


def compare_control_treated(
    samples: list[SampleRecord],
    control_group: str,
    treated_group: str,
    group_field: str = "condition",
    channels: list[str] | None = None,
    use_compensation: bool = False,
) -> list[ComparisonResult]:
    """Run exploratory median/MFI-style comparison between two groups."""
    grouped: dict[str, list[SampleRecord]] = defaultdict(list)
    for sample in samples:
        grouped[str(getattr(sample, group_field, "") or "")].append(sample)
    control = grouped.get(control_group, [])
    treated = grouped.get(treated_group, [])
    channels = channels or sorted({channel for sample in samples for channel in sample.fluorescence_channels})
    results: list[ComparisonResult] = []
    for channel in channels:
        control_values = _sample_medians(control, channel, use_compensation)
        treated_values = _sample_medians(treated, channel, use_compensation)
        control_median = _median_or_none(control_values)
        treated_median = _median_or_none(treated_values)
        diff = None if control_median is None or treated_median is None else treated_median - control_median
        notes: list[str] = ["exploratory only"]
        fold, fold_note = _guarded_fold_change(control_median, treated_median)
        if fold_note:
            notes.append(fold_note)
        if len(control_values) < 2 or len(treated_values) < 2:
            notes.append("replicate count is too low for inferential statistics")
        results.append(
            ComparisonResult(
                channel,
                control_median,
                treated_median,
                diff,
                fold,
                len(control_values),
                len(treated_values),
                notes,
            )
        )
    return results


def _sample_medians(samples: list[SampleRecord], channel: str, use_compensation: bool) -> list[float]:
    values: list[float] = []
    for sample in samples:
        events = event_view(sample, use_compensation)
        if channel in events:
            median = _series_median_or_none(events[channel])
            if median is not None:
                values.append(float(median))
    return values


def _median_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    median = float(np.median(values))
    return median if np.isfinite(median) else None


def _series_median_or_none(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    median = numeric.median()
    if pd.isna(median) or not np.isfinite(float(median)):
        return None
    return float(median)


def _guarded_fold_change(control_median: float | None, treated_median: float | None, epsilon: float = 1e-9) -> tuple[float | None, str | None]:
    if control_median is None or treated_median is None:
        return None, None
    if not np.isfinite(control_median) or not np.isfinite(treated_median):
        return None, "fold-change not computed because at least one median is not finite"
    if control_median <= epsilon or treated_median < 0:
        return None, "fold-change not computed for negative or near-zero medians; use median difference"
    return treated_median / control_median, None
