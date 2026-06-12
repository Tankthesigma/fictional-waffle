from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from app.core.channel_labels import channel_label_map
from app.core.compensation import event_view
from app.core.gating import apply_gate_tree
from app.core.stats import gate_statistics
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


def batch_gate_statistics_table(samples: list[SampleRecord], gates, use_compensation: bool = False) -> list[dict[str, object]]:
    """Apply compatible gates to every sample and return a compact batch grid."""
    rows: list[dict[str, object]] = []
    for sample in samples:
        events = event_view(sample, use_compensation)
        view_name = "metadata_compensated" if use_compensation and sample.compensated_events is not None else "raw"
        compatible = [gate for gate in gates if gate.metadata.get("event_view", "raw") == view_name]
        masks = apply_gate_tree(events, compatible)
        for row in gate_statistics(events, compatible, masks, sample.fluorescence_channels):
            rows.append(
                {
                    "gate_id": row.get("gate_id"),
                    "sample_id": sample.sample_id,
                    "condition": sample.condition or "",
                    "replicate": sample.replicate or "",
                    "gate_name": row.get("gate_name"),
                    "parent_gate": row.get("parent_gate"),
                    "event_count": row.get("event_count"),
                    "percent_total": row.get("percent_total"),
                    "percent_parent": row.get("percent_parent"),
                    "gate_warning": row.get("gate_warning", ""),
                }
            )
    return rows


def population_frequency_table(samples: list[SampleRecord], gates, use_compensation: bool = False) -> list[dict[str, object]]:
    """Return a population-by-sample percent-parent matrix for cohort review."""
    if not samples or not gates:
        return []
    rows_by_gate: dict[str, dict[str, object]] = {}
    for sample in samples:
        events = event_view(sample, use_compensation)
        view_name = "metadata_compensated" if use_compensation and sample.compensated_events is not None else "raw"
        compatible = [gate for gate in gates if gate.metadata.get("event_view", "raw") == view_name]
        masks = apply_gate_tree(events, compatible)
        for row in gate_statistics(events, compatible, masks, sample.fluorescence_channels):
            gate_id = str(row.get("gate_id") or row.get("gate_name"))
            frequency_row = rows_by_gate.setdefault(
                gate_id,
                {
                    "population": row.get("gate_name"),
                    "gate_id": gate_id,
                    "parent_gate": row.get("parent_gate"),
                    "gate_warning": row.get("gate_warning", ""),
                },
            )
            frequency_row[sample.sample_id] = row.get("percent_parent")
            frequency_row[f"{sample.sample_id}_count"] = row.get("event_count")
    return list(rows_by_gate.values())


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
    labels = channel_label_map(samples)
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
                labels.get(channel, channel),
                notes,
            )
        )
    return results


def comparison_summary(rows: list[ComparisonResult | dict[str, object]]) -> list[dict[str, object]]:
    """Summarize exploratory comparison rows for the UI.

    The summary intentionally describes median differences and guardrails; it
    does not assign statistical or biological significance.
    """
    normalized = [_row_dict(row) for row in rows]
    comparable = [row for row in normalized if _number_or_none(row.get("median_difference")) is not None]
    guarded = [row for row in normalized if "fold-change not computed" in str(row.get("notes", ""))]
    low_replicate = [row for row in normalized if "replicate count is too low" in str(row.get("notes", ""))]
    strongest_up = _extreme_difference(comparable, direction="up")
    strongest_down = _extreme_difference(comparable, direction="down")
    return [
        {
            "label": "Compared Channels",
            "value": len(normalized),
            "detail": "exploratory fluorescence median rows",
            "tone": "",
        },
        {
            "label": "Strongest Increase",
            "value": _difference_label(strongest_up),
            "detail": _channel_detail(strongest_up),
            "tone": "positive" if strongest_up else "",
        },
        {
            "label": "Strongest Decrease",
            "value": _difference_label(strongest_down),
            "detail": _channel_detail(strongest_down),
            "tone": "warning" if strongest_down else "",
        },
        {
            "label": "Guarded Fold-Changes",
            "value": len(guarded),
            "detail": "hidden for negative, non-finite, or near-zero medians",
            "tone": "warning" if guarded else "",
        },
        {
            "label": "Low-Replicate Rows",
            "value": len(low_replicate),
            "detail": "descriptive only; no inferential claim",
            "tone": "warning" if low_replicate else "",
        },
    ]


def comparison_insights(
    rows: list[ComparisonResult | dict[str, object]],
    control_group: str | None = None,
    treated_group: str | None = None,
) -> list[dict[str, str]]:
    """Create plain-English review notes for exploratory comparison results."""
    normalized = [_row_dict(row) for row in rows]
    if not normalized:
        return [
            {
                "severity": "waiting",
                "title": "Choose Groups",
                "message": "Select control and treated groups to generate exploratory comparison notes.",
                "detail": "No statistical or biological interpretation is made automatically.",
            }
        ]

    comparable = [row for row in normalized if _number_or_none(row.get("median_difference")) is not None]
    increases = [row for row in comparable if (_number_or_none(row.get("median_difference")) or 0) > 0]
    decreases = [row for row in comparable if (_number_or_none(row.get("median_difference")) or 0) < 0]
    guarded = [row for row in normalized if "fold-change not computed" in str(row.get("notes", ""))]
    low_replicate = [row for row in normalized if "replicate count is too low" in str(row.get("notes", ""))]
    strongest = _strongest_absolute_difference(comparable)
    group_label = _group_label(control_group, treated_group)

    insights = [
        {
            "severity": "info",
            "title": "Comparison Scope",
            "message": f"{len(normalized)} fluorescence channel row(s) compared{group_label}.",
            "detail": "Values are descriptive medians; review replicate structure before making claims.",
        },
        {
            "severity": "review" if strongest else "info",
            "title": "Largest Median Shift",
            "message": _largest_shift_message(strongest),
            "detail": "Use marker labels and gates to decide whether this shift is meaningful for the experiment.",
        },
        {
            "severity": "info",
            "title": "Direction Count",
            "message": f"{len(increases)} channel(s) higher and {len(decreases)} channel(s) lower in treated medians.",
            "detail": "Direction is based only on treated median minus control median.",
        },
    ]
    if guarded:
        insights.append(
            {
                "severity": "warning",
                "title": "Guarded Fold-Changes",
                "message": f"{len(guarded)} row(s) hide fold-change because medians were negative, non-finite, or near zero.",
                "detail": "Use median difference for compensated data and review the underlying distributions.",
            }
        )
    if low_replicate:
        insights.append(
            {
                "severity": "warning",
                "title": "Low Replicate Review",
                "message": f"{len(low_replicate)} row(s) have too few replicates for inferential statistics.",
                "detail": "Treat these as screening notes until replicate structure is reviewed.",
            }
        )
    return insights


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


def _row_dict(row: ComparisonResult | dict[str, object]) -> dict[str, object]:
    return row.to_dict() if isinstance(row, ComparisonResult) else row


def _number_or_none(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _extreme_difference(rows: list[dict[str, object]], direction: str) -> dict[str, object] | None:
    candidates = []
    for row in rows:
        diff = _number_or_none(row.get("median_difference"))
        if diff is None:
            continue
        if direction == "up" and diff > 0:
            candidates.append((diff, row))
        elif direction == "down" and diff < 0:
            candidates.append((abs(diff), row))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _difference_label(row: dict[str, object] | None) -> str:
    if not row:
        return "none"
    diff = _number_or_none(row.get("median_difference"))
    if diff is None:
        return "none"
    return f"{diff:+.3g}"


def _channel_detail(row: dict[str, object] | None) -> str:
    if not row:
        return "no directional median shift detected"
    return f"{row.get('channel_label') or row.get('channel', 'channel')} median difference; exploratory only"


def _strongest_absolute_difference(rows: list[dict[str, object]]) -> dict[str, object] | None:
    candidates = []
    for row in rows:
        diff = _number_or_none(row.get("median_difference"))
        if diff is not None:
            candidates.append((abs(diff), row))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _largest_shift_message(row: dict[str, object] | None) -> str:
    if not row:
        return "No finite median shifts were available for review."
    diff = _number_or_none(row.get("median_difference"))
    direction = "higher" if diff is not None and diff > 0 else "lower"
    channel = row.get("channel_label") or row.get("channel", "channel")
    return f"{channel} is {direction} in treated medians by {_difference_label(row)}."


def _group_label(control_group: str | None, treated_group: str | None) -> str:
    if control_group and treated_group:
        return f" between {control_group} and {treated_group}"
    return ""
