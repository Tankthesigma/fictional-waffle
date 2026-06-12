from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from app.core.channel_inference import best_scatter_pair
from app.core.gating import rectangle_gate
from app.core.high_dimensional import high_dimensional_review
from app.models.gate import GateDefinition
from app.models.sample import SampleRecord

ClusterLabeler = Callable[[SampleRecord, list[dict[str, object]]], dict[int, str]]


@dataclass(slots=True)
class AutoGateResult:
    """Review-needed autogating result."""

    gates: list[GateDefinition]
    cluster_rows: list[dict[str, object]]
    warnings: list[str]


def suggest_ai_auto_gates(
    sample: SampleRecord | None,
    *,
    x_channel: str | None = None,
    y_channel: str | None = None,
    n_clusters: int = 6,
    max_events: int = 50_000,
    reducer: str = "umap",
    id_prefix: str = "ai_auto",
    labeler: ClusterLabeler | None = None,
) -> AutoGateResult:
    """Suggest review-needed gates from fluorescence clustering.

    The output is deliberately conservative: each cluster becomes a disabled
    rectangle gate on the current 2-D plot, bounded by robust quantiles of the
    clustered events. Labels describe marker patterns when available, but the
    gates remain candidate/review-needed until a human accepts or edits them.
    """
    if sample is None:
        return AutoGateResult([], [], ["Select a sample before running cluster-guided gate review."])
    x_channel, y_channel = _resolve_gate_axes(sample, x_channel, y_channel)
    if not x_channel or not y_channel:
        return AutoGateResult([], [], ["Choose two plot channels before running cluster-guided gate review."])
    if x_channel not in sample.events or y_channel not in sample.events:
        return AutoGateResult([], [], ["Selected plot channels are not available in the sample event table."])

    review = high_dimensional_review(sample, n_clusters=n_clusters, max_events=max_events, reducer=reducer)
    if review.embedding.empty or review.clusters.empty:
        return AutoGateResult([], [], list(review.warnings))
    cluster_rows = review.clusters.to_dict("records")
    labels = labeler(sample, cluster_rows) if labeler else {}
    gates: list[GateDefinition] = []
    for row in cluster_rows:
        cluster_id = int(row["cluster"])
        event_indices = review.embedding.loc[review.embedding["cluster"] == cluster_id, "event_index"].to_list()
        bounds = _cluster_bounds(sample.events, event_indices, x_channel, y_channel)
        if bounds is None:
            continue
        label = labels.get(cluster_id) or _deterministic_cluster_label(sample, row)
        gate = rectangle_gate(
            f"{id_prefix}_{sample.sample_id}_{cluster_id}",
            label,
            x_channel,
            y_channel,
            bounds["x_min"],
            bounds["x_max"],
            bounds["y_min"],
            bounds["y_max"],
        )
        gate.enabled = False
        gate.candidate = True
        gate.user_defined = False
        gate.review_status = "review_needed"
        gate.metadata.update(
            {
                "event_view": "raw",
                "candidate_reason": "Cluster-derived footprint; review/edit before using final statistics",
                "auto_gate": "cluster-derived rectangle on current plot",
                "embedding": review.reducer,
                "cluster_id": cluster_id,
                "cluster_event_count": int(row.get("event_count", 0)),
                "cluster_percent_total": float(row.get("percent_total", 0.0)),
                "label_source": "enhanced_assistant" if cluster_id in labels else "deterministic_marker_summary",
                "identity_warning": "Review-needed only; do not treat this as a confirmed biological identity.",
            }
        )
        gates.append(gate)
    warnings = list(review.warnings)
    if not gates:
        warnings.append("No stable cluster gates could be projected onto the selected plot channels.")
    return AutoGateResult(gates, cluster_rows, warnings)


def _resolve_gate_axes(sample: SampleRecord, x_channel: str | None, y_channel: str | None) -> tuple[str | None, str | None]:
    if x_channel and y_channel:
        return x_channel, y_channel
    fsc, ssc = best_scatter_pair(sample.channels)
    return x_channel or fsc, y_channel or ssc


def _cluster_bounds(events: pd.DataFrame, event_indices: list[object], x_channel: str, y_channel: str) -> dict[str, float] | None:
    frame = events.loc[event_indices, [x_channel, y_channel]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 5:
        return None
    x_min, x_max = frame[x_channel].quantile([0.02, 0.98])
    y_min, y_max = frame[y_channel].quantile([0.02, 0.98])
    if not all(np.isfinite(value) for value in [x_min, x_max, y_min, y_max]) or x_min >= x_max or y_min >= y_max:
        return None
    return {"x_min": float(x_min), "x_max": float(x_max), "y_min": float(y_min), "y_max": float(y_max)}


def _deterministic_cluster_label(sample: SampleRecord, row: dict[str, object]) -> str:
    cluster = int(row.get("cluster", 0))
    median_items = [(key.removesuffix("_median"), float(value)) for key, value in row.items() if key.endswith("_median") and isinstance(value, int | float)]
    median_items.sort(key=lambda item: item[1], reverse=True)
    labels = _channel_labels(sample)
    top = ", ".join(labels.get(channel, channel) for channel, _value in median_items[:2])
    if top:
        return f"Cluster {cluster} review: {top} high"
    return f"Cluster {cluster} review"


def _channel_labels(sample: SampleRecord) -> dict[str, str]:
    return {channel.raw_name: channel.label for channel in sample.channels}
