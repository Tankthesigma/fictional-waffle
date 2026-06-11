from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from app.models.qc_flag import QCFlag
from app.models.sample import SampleRecord


@dataclass(slots=True)
class QCThresholds:
    low_event_warning: int = 5_000
    low_event_severe: int = 1_000
    clipping_percent_warning: float = 1.0
    debris_fraction_warning: float = 25.0
    doublet_deviation_warning: float = 20.0
    time_cv_warning: float = 0.35
    batch_z_warning: float = 3.0


def run_sample_qc(sample: SampleRecord, thresholds: QCThresholds | None = None) -> list[QCFlag]:
    """Run rule-based QC checks for one sample."""
    thresholds = thresholds or QCThresholds()
    flags: list[QCFlag] = []
    if sample.event_count < thresholds.low_event_severe:
        flags.append(_flag(sample.sample_id, "severe", "LOW_EVENTS_SEVERE", "Very low event count", sample.event_count, thresholds.low_event_severe, ["plotting", "gating", "comparison", "reporting"]))
    elif sample.event_count < thresholds.low_event_warning:
        flags.append(_flag(sample.sample_id, "warning", "LOW_EVENTS", "Low event count", sample.event_count, thresholds.low_event_warning, ["gating", "comparison"]))

    if not sample.channel_by_role("fsc") or not sample.channel_by_role("ssc"):
        flags.append(
            QCFlag(
                sample.sample_id,
                "warning",
                "MISSING_FSC_SSC",
                "FSC/SSC channels were not confidently identified",
                "The channel inference rules could not find both scatter channels. This can affect default plots and scatter-based gates.",
                "missing",
                "at least one FSC and one SSC channel",
                "Review channel names and set manual channel roles if needed.",
                ["plotting", "gating"],
            )
        )
    if not sample.channel_by_role("time"):
        flags.append(
            QCFlag(
                sample.sample_id,
                "info",
                "MISSING_TIME",
                "No Time channel detected",
                "The exported data does not appear to include a Time channel, so acquisition stability can only be reviewed outside this app.",
                "missing",
                "Time channel present",
                "Time stability plots are unavailable for this sample.",
                ["qc"],
            )
        )

    roles = {channel.role for channel in sample.channels}
    if not any(role.endswith("-h") or role.endswith("-w") for role in roles):
        flags.append(
            QCFlag(
                sample.sample_id,
                "info",
                "MISSING_PULSE_GEOMETRY",
                "Pulse geometry channels appear incomplete",
                "Area/height/width-style channels were not all detected, so doublet diagnostics are limited.",
                "missing height/width",
                "area plus height or width channels",
                "Singlet-style diagnostics may be limited.",
                ["gating", "qc"],
            )
        )

    for channel in sample.channels:
        if channel.percent_near_max >= thresholds.clipping_percent_warning:
            flags.append(
                QCFlag(
                    sample.sample_id,
                    "warning",
                    "POSSIBLE_HIGH_CLIPPING",
                    "Possible high-end clipping",
                    "A notable fraction of events are close to the observed channel maximum, which may indicate saturation or export range clipping.",
                    round(channel.percent_near_max, 3),
                    thresholds.clipping_percent_warning,
                    "Inspect the channel histogram and confirm whether values pile up near the detector range.",
                    ["plotting", "gating", "comparison"],
                    channel.raw_name,
                )
            )
        if channel.percent_near_min >= thresholds.clipping_percent_warning:
            flags.append(
                QCFlag(
                    sample.sample_id,
                    "info",
                    "POSSIBLE_LOW_CLIPPING",
                    "Possible low-end clipping",
                    "A notable fraction of events are close to the observed channel minimum, which can affect low-end histogram interpretation.",
                    round(channel.percent_near_min, 3),
                    thresholds.clipping_percent_warning,
                    "Inspect the channel histogram for a pile-up at the lower bound.",
                    ["plotting", "qc"],
                    channel.raw_name,
                )
            )

    flags.extend(_debris_check(sample, thresholds))
    flags.extend(_doublet_check(sample, thresholds))
    flags.extend(_time_stability_check(sample, thresholds))
    if sample.spillover is not None and sample.compensated_events is None:
        flags.append(
            QCFlag(
                sample.sample_id,
                "warning",
                "COMPENSATION_METADATA_NOT_APPLIED",
                "Compensation metadata was detected but not applied",
                "Spillover metadata exists, but the matrix could not be applied cleanly to the event table.",
                "; ".join(sample.compensation_warnings or sample.spillover.warnings) or "not applied",
                "valid square spillover matrix with matching channel labels",
                "Review the FCS spillover keyword and confirm whether exported values are already compensated.",
                ["plotting", "comparison", "reporting"],
            )
        )
    if _has_fluorescence(sample) and not _has_spillover(sample.keywords):
        flags.append(
            QCFlag(
                sample.sample_id,
                "info",
                "NO_SPILLOVER_METADATA",
                "No spillover or compensation metadata found",
                "Multiple fluorescence channels were detected, but the FCS keywords do not expose spillover metadata.",
                "not found",
                "$SPILL or $SPILLOVER keyword",
                "If the panel needs compensation, confirm whether exported values are already compensated.",
                ["plotting", "comparison", "reporting"],
            )
        )
    return flags


def run_batch_qc(samples: Iterable[SampleRecord], thresholds: QCThresholds | None = None) -> dict[str, list[QCFlag]]:
    """Run per-sample QC plus simple batch outlier checks."""
    thresholds = thresholds or QCThresholds()
    sample_list = list(samples)
    results = {sample.sample_id: run_sample_qc(sample, thresholds) for sample in sample_list}
    if len(sample_list) < 3:
        return results
    counts = np.array([sample.event_count for sample in sample_list], dtype=float)
    count_z = _robust_z(counts)
    for sample, z in zip(sample_list, count_z, strict=False):
        if abs(z) >= thresholds.batch_z_warning:
            results[sample.sample_id].append(
                QCFlag(
                    sample.sample_id,
                    "warning",
                    "BATCH_EVENT_COUNT_OUTLIER",
                    "Event count is an outlier within this batch",
                    "This sample's event count is far from the batch median by a robust z-score heuristic.",
                    round(float(z), 3),
                    thresholds.batch_z_warning,
                    "Review acquisition notes and whether this sample should be compared with the same batch.",
                    ["comparison", "reporting"],
                )
            )
    return results


def qc_summary(flags: list[QCFlag]) -> str:
    severities = [flag.severity for flag in flags]
    if "severe" in severities:
        return "severe review needed"
    if "warning" in severities:
        return "review needed"
    if "info" in severities:
        return "info"
    return "no flags"


def _flag(sample_id: str, severity: str, code: str, title: str, metric: object, threshold: object, affects: list[str]) -> QCFlag:
    return QCFlag(
        sample_id,
        severity,  # type: ignore[arg-type]
        code,
        title,
        f"{title}. This is a rule-based warning for human review, not a biological conclusion.",
        metric,
        threshold,
        "Confirm whether the sample has enough usable events for the intended analysis.",
        affects,
    )


def _debris_check(sample: SampleRecord, thresholds: QCThresholds) -> list[QCFlag]:
    fsc = sample.channel_by_role("fsc")
    ssc = sample.channel_by_role("ssc")
    if not fsc or not ssc or fsc.raw_name not in sample.events or ssc.raw_name not in sample.events:
        return []
    fsc_values = pd.to_numeric(sample.events[fsc.raw_name], errors="coerce")
    ssc_values = pd.to_numeric(sample.events[ssc.raw_name], errors="coerce")
    low_fsc = fsc_values <= fsc_values.quantile(0.2)
    low_ssc = ssc_values <= ssc_values.quantile(0.2)
    fraction = float((low_fsc & low_ssc).mean() * 100.0)
    if fraction >= thresholds.debris_fraction_warning:
        return [
            QCFlag(
                sample.sample_id,
                "warning",
                "DEBRIS_HEAVY_HEURISTIC",
                "Low FSC/SSC event burden is elevated",
                "A high fraction of events are jointly low in FSC and SSC relative to this sample's distribution.",
                round(fraction, 3),
                thresholds.debris_fraction_warning,
                "Review the FSC/SSC plot for debris-like low-scatter events before final gating.",
                ["plotting", "gating"],
            )
        ]
    return []


def _doublet_check(sample: SampleRecord, thresholds: QCThresholds) -> list[QCFlag]:
    pairs = [("fsc-a", "fsc-h"), ("fsc-a", "fsc-w"), ("ssc-a", "ssc-h"), ("ssc-a", "ssc-w")]
    for area_role, other_role in pairs:
        area = sample.channel_by_role(area_role)
        other = sample.channel_by_role(other_role)
        if not area or not other or area.raw_name not in sample.events or other.raw_name not in sample.events:
            continue
        x = pd.to_numeric(sample.events[area.raw_name], errors="coerce").to_numpy(dtype=float)
        y = pd.to_numeric(sample.events[other.raw_name], errors="coerce").to_numpy(dtype=float)
        valid = np.isfinite(x) & np.isfinite(y)
        if valid.sum() < 100:
            continue
        ratio = y[valid] / np.maximum(x[valid], 1e-9)
        spread = float((np.nanpercentile(ratio, 95) - np.nanpercentile(ratio, 5)) * 100.0)
        if spread >= thresholds.doublet_deviation_warning:
            return [
                QCFlag(
                    sample.sample_id,
                    "warning",
                    "POSSIBLE_DOUBLET_BURDEN",
                    "Pulse geometry spread is broad",
                    "The relationship between pulse geometry channels is broad by a simple ratio-spread heuristic.",
                    round(spread, 3),
                    thresholds.doublet_deviation_warning,
                    "Review area/height or area/width plots before relying on singlet-style gates.",
                    ["gating", "qc"],
                )
            ]
    return []


def _time_stability_check(sample: SampleRecord, thresholds: QCThresholds) -> list[QCFlag]:
    time_channel = sample.channel_by_role("time")
    if not time_channel or time_channel.raw_name not in sample.events or sample.event_count < 100:
        return []
    values = pd.to_numeric(sample.events[time_channel.raw_name], errors="coerce").to_numpy(dtype=float)
    valid = values[np.isfinite(values)]
    if valid.size < 100 or np.nanmax(valid) == np.nanmin(valid):
        return []
    counts, _ = np.histogram(valid, bins=20)
    cv = float(np.std(counts) / max(np.mean(counts), 1e-9))
    if cv >= thresholds.time_cv_warning:
        return [
            QCFlag(
                sample.sample_id,
                "warning",
                "UNSTABLE_ACQUISITION_HEURISTIC",
                "Event rate varies over Time",
                "Event counts over time bins vary enough to warrant review for spikes, troughs, or drift.",
                round(cv, 3),
                thresholds.time_cv_warning,
                "Inspect the time stability plot for spikes, troughs, or drift.",
                ["qc", "reporting"],
            )
        ]
    return []


def _robust_z(values: np.ndarray) -> np.ndarray:
    median = np.nanmedian(values)
    mad = np.nanmedian(np.abs(values - median))
    if mad == 0:
        return np.zeros_like(values)
    return 0.6745 * (values - median) / mad


def _has_fluorescence(sample: SampleRecord) -> bool:
    return any(channel.role == "fluorescence" for channel in sample.channels)


def _has_spillover(keywords: dict[str, object]) -> bool:
    keys = {str(key).lower().strip("$") for key in keywords}
    return "spill" in keys or "spillover" in keys or "comp" in keys
