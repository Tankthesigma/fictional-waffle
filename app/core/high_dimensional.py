from __future__ import annotations

from dataclasses import dataclass
import logging

import numpy as np
import pandas as pd

from app.core.downsample import downsample_events
from app.models.sample import SampleRecord

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClusterReviewResult:
    """Deterministic high-dimensional review output, not cell identity calling."""

    embedding: pd.DataFrame
    clusters: pd.DataFrame
    warnings: list[str]
    reducer: str = "pca"


def high_dimensional_review(
    sample: SampleRecord | None,
    channels: list[str] | None = None,
    *,
    reducer: str = "umap",
    n_clusters: int = 6,
    max_events: int = 50_000,
    random_state: int = 7,
) -> ClusterReviewResult:
    """Embed fluorescence data and cluster it for review-needed inspection.

    UMAP is preferred for nonlinear population separation. PCA remains the
    deterministic fallback. This does not infer cell identity; marker meaning
    must come from the user/panel metadata.
    """
    if sample is None:
        return ClusterReviewResult(pd.DataFrame(), pd.DataFrame(), ["Select a sample before running high-dimensional review."], reducer=reducer)
    selected = channels or sample.fluorescence_channels
    selected = [channel for channel in selected if channel in sample.events]
    if len(selected) < 2:
        return ClusterReviewResult(
            pd.DataFrame(),
            pd.DataFrame(),
            ["High-dimensional review needs at least two numeric fluorescence channels."],
            reducer=reducer,
        )
    frame = downsample_events(sample.events[selected], max_events=max_events)
    numeric = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(numeric) < max(10, n_clusters):
        return ClusterReviewResult(pd.DataFrame(), pd.DataFrame(), ["Not enough finite events for clustering review."], reducer=reducer)

    from sklearn.cluster import MiniBatchKMeans
    from sklearn.preprocessing import StandardScaler

    warnings: list[str] = []
    scaled = StandardScaler().fit_transform(numeric.to_numpy(dtype=float))
    embedding_values, reducer_used, reducer_warnings = _embed_events(scaled, reducer=reducer, random_state=random_state)
    warnings.extend(reducer_warnings)
    cluster_count = max(2, min(int(n_clusters), len(numeric)))
    labels = MiniBatchKMeans(n_clusters=cluster_count, random_state=random_state, n_init=5, batch_size=4096).fit_predict(scaled)
    embedding_payload = {
        "sample_id": sample.sample_id,
        "event_index": numeric.index.to_list(),
        "dim1": embedding_values[:, 0],
        "dim2": embedding_values[:, 1],
        "cluster": labels,
        "reducer": reducer_used,
    }
    if reducer_used == "umap":
        embedding_payload["umap1"] = embedding_values[:, 0]
        embedding_payload["umap2"] = embedding_values[:, 1]
    else:
        embedding_payload["pc1"] = embedding_values[:, 0]
        embedding_payload["pc2"] = embedding_values[:, 1]
    embedding = pd.DataFrame(embedding_payload, index=numeric.index)
    clusters = _cluster_summary(numeric, labels)
    warnings.append(f"{reducer_used.upper()} clusters are exploratory review aids; assign biological labels only with marker context.")
    return ClusterReviewResult(embedding, clusters, warnings, reducer=reducer_used)


def pca_cluster_review(
    sample: SampleRecord | None,
    channels: list[str] | None = None,
    *,
    n_clusters: int = 6,
    max_events: int = 50_000,
    random_state: int = 7,
) -> ClusterReviewResult:
    """Compatibility wrapper for deterministic PCA review."""
    return high_dimensional_review(sample, channels, reducer="pca", n_clusters=n_clusters, max_events=max_events, random_state=random_state)


def umap_cluster_review(
    sample: SampleRecord | None,
    channels: list[str] | None = None,
    *,
    n_clusters: int = 6,
    max_events: int = 50_000,
    random_state: int = 7,
) -> ClusterReviewResult:
    """Run UMAP-backed high-dimensional review with PCA fallback."""
    return high_dimensional_review(sample, channels, reducer="umap", n_clusters=n_clusters, max_events=max_events, random_state=random_state)


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


def _embed_events(scaled: np.ndarray, *, reducer: str, random_state: int) -> tuple[np.ndarray, str, list[str]]:
    requested = (reducer or "umap").strip().lower()
    if requested == "umap":
        try:
            import umap  # type: ignore

            n_neighbors = max(2, min(15, len(scaled) - 1))
            embedding = umap.UMAP(
                n_components=2,
                n_neighbors=n_neighbors,
                min_dist=0.12,
                metric="euclidean",
                random_state=random_state,
            ).fit_transform(scaled)
            return np.asarray(embedding, dtype=float), "umap", []
        except Exception as exc:
            logger.exception("UMAP embedding failed; falling back to PCA")
            pca_values = _pca_embedding(scaled, random_state)
            return pca_values, "pca", [f"UMAP was unavailable or could not run ({exc}); PCA fallback shown."]
    return _pca_embedding(scaled, random_state), "pca", []


def _pca_embedding(scaled: np.ndarray, random_state: int) -> np.ndarray:
    from sklearn.decomposition import PCA

    return PCA(n_components=2, random_state=random_state).fit_transform(scaled)
