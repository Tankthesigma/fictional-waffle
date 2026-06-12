from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.downsample import downsample_events
from app.models.sample import SampleRecord


@dataclass(slots=True)
class ClusterReviewResult:
    """Deterministic high-dimensional review output, not cell identity calling."""

    embedding: pd.DataFrame
    clusters: pd.DataFrame
    warnings: list[str]


def pca_cluster_review(
    sample: SampleRecord | None,
    channels: list[str] | None = None,
    *,
    n_clusters: int = 6,
    max_events: int = 50_000,
    random_state: int = 7,
) -> ClusterReviewResult:
    """Embed fluorescence data with PCA and cluster it for review-needed inspection.

    This is intentionally deterministic and descriptive. It does not infer
    cell identity; marker meaning must come from the user/panel metadata.
    """
    if sample is None:
        return ClusterReviewResult(pd.DataFrame(), pd.DataFrame(), ["Select a sample before running high-dimensional review."])
    selected = channels or sample.fluorescence_channels
    selected = [channel for channel in selected if channel in sample.events]
    if len(selected) < 2:
        return ClusterReviewResult(pd.DataFrame(), pd.DataFrame(), ["High-dimensional review needs at least two numeric fluorescence channels."])
    frame = downsample_events(sample.events[selected], max_events=max_events)
    numeric = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(numeric) < max(10, n_clusters):
        return ClusterReviewResult(pd.DataFrame(), pd.DataFrame(), ["Not enough finite events for clustering review."])

    from sklearn.cluster import MiniBatchKMeans
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    scaled = StandardScaler().fit_transform(numeric.to_numpy(dtype=float))
    embedding_values = PCA(n_components=2, random_state=random_state).fit_transform(scaled)
    cluster_count = max(2, min(int(n_clusters), len(numeric)))
    labels = MiniBatchKMeans(n_clusters=cluster_count, random_state=random_state, n_init=5, batch_size=4096).fit_predict(scaled)
    embedding = pd.DataFrame({"sample_id": sample.sample_id, "pc1": embedding_values[:, 0], "pc2": embedding_values[:, 1], "cluster": labels})
    clusters = _cluster_summary(numeric, labels)
    return ClusterReviewResult(embedding, clusters, ["Clusters are exploratory review aids; assign biological labels only with marker context."])


def _cluster_summary(events: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label in sorted(set(int(item) for item in labels)):
        mask = labels == label
        row: dict[str, object] = {
            "cluster": label,
            "event_count": int(mask.sum()),
            "percent_total": round(float(mask.mean() * 100.0), 3),
        }
        cluster_frame = events.loc[mask]
        for channel in events.columns:
            row[f"{channel}_median"] = float(cluster_frame[channel].median())
        rows.append(row)
    return pd.DataFrame(rows).sort_values("event_count", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
