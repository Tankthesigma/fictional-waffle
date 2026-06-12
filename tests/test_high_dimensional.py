import numpy as np
import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.high_dimensional import pca_cluster_review, umap_cluster_review
from app.models.sample import SampleRecord


def test_pca_cluster_review_is_deterministic_and_review_labeled():
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(
        {
            "FL1-A": np.r_[rng.normal(10, 1, 80), rng.normal(40, 1, 80)],
            "FL2-A": np.r_[rng.normal(8, 1, 80), rng.normal(35, 1, 80)],
            "FL3-A": np.r_[rng.normal(20, 1, 80), rng.normal(5, 1, 80)],
        }
    )
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)

    first = pca_cluster_review(sample, n_clusters=2, random_state=11)
    second = pca_cluster_review(sample, n_clusters=2, random_state=11)

    assert first.warnings == ["PCA clusters are exploratory review aids; assign biological labels only with marker context."]
    assert first.embedding[["pc1", "pc2", "cluster"]].round(8).equals(second.embedding[["pc1", "pc2", "cluster"]].round(8))
    assert first.embedding[["dim1", "dim2", "cluster"]].round(8).equals(second.embedding[["dim1", "dim2", "cluster"]].round(8))
    assert first.embedding["event_index"].tolist() == list(range(len(frame)))
    assert first.clusters["event_count"].sum() == len(frame)
    assert set(first.clusters["cluster"]) == {0, 1}
    assert first.reducer == "pca"


def test_umap_cluster_review_is_deterministic_when_available():
    rng = np.random.default_rng(9)
    frame = pd.DataFrame(
        {
            "FL1-A": np.r_[rng.normal(10, 1, 60), rng.normal(45, 1, 60)],
            "FL2-A": np.r_[rng.normal(8, 1, 60), rng.normal(34, 1, 60)],
            "FL3-A": np.r_[rng.normal(22, 1, 60), rng.normal(6, 1, 60)],
        }
    )
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)

    first = umap_cluster_review(sample, n_clusters=2, random_state=12)
    second = umap_cluster_review(sample, n_clusters=2, random_state=12)

    assert first.reducer in {"umap", "pca"}
    assert first.embedding[["dim1", "dim2", "cluster"]].round(6).equals(second.embedding[["dim1", "dim2", "cluster"]].round(6))
    assert first.clusters["event_count"].sum() == len(frame)
    assert any("exploratory review aids" in warning for warning in first.warnings)


def test_pca_cluster_review_requires_two_channels():
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=pd.DataFrame({"FL1-A": [1, 2, 3]}))
    sample.channels = summarize_channels(sample.events)

    result = pca_cluster_review(sample)

    assert result.embedding.empty
    assert "at least two" in result.warnings[0]
