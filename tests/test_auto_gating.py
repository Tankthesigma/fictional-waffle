import numpy as np
import pandas as pd

from app.core.auto_gating import suggest_ai_auto_gates
from app.core.channel_inference import summarize_channels
from app.core.gating import apply_gate_tree
from app.models.sample import SampleRecord


def _cluster_sample() -> SampleRecord:
    rng = np.random.default_rng(11)
    frame = pd.DataFrame(
        {
            "FSC-A": np.r_[rng.normal(100, 5, 80), rng.normal(300, 5, 80)],
            "SSC-A": np.r_[rng.normal(90, 5, 80), rng.normal(250, 5, 80)],
            "FL1-A": np.r_[rng.normal(10, 1, 80), rng.normal(100, 1, 80)],
            "FL2-A": np.r_[rng.normal(90, 1, 80), rng.normal(15, 1, 80)],
        }
    )
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = summarize_channels(frame)
    sample.channels[2].marker = "CD3"
    sample.channels[2].fluorochrome = "FITC"
    sample.channels[3].marker = "CD19"
    sample.channels[3].fluorochrome = "PE"
    return sample


def test_ai_auto_gates_create_disabled_review_needed_cluster_candidates():
    sample = _cluster_sample()

    result = suggest_ai_auto_gates(sample, x_channel="FSC-A", y_channel="SSC-A", n_clusters=2, id_prefix="auto")

    assert len(result.gates) == 2
    assert all(gate.candidate for gate in result.gates)
    assert all(not gate.enabled for gate in result.gates)
    assert all(gate.review_status == "review_needed" for gate in result.gates)
    assert all("review" in gate.metadata["candidate_reason"].lower() for gate in result.gates)
    assert all(gate.metadata["identity_warning"].startswith("Review-needed") for gate in result.gates)
    assert {gate.metadata["embedding"] for gate in result.gates} <= {"umap", "pca"}
    assert all("CD" in gate.name for gate in result.gates)
    masks = apply_gate_tree(sample.events, result.gates)
    assert all(not mask.any() for mask in masks.values())


def test_ai_auto_gates_use_optional_enhanced_labels_without_enabling_gates():
    sample = _cluster_sample()

    def labeler(_sample, rows):
        return {int(row["cluster"]): f"Enhanced cluster {int(row['cluster'])} review" for row in rows}

    result = suggest_ai_auto_gates(sample, x_channel="FSC-A", y_channel="SSC-A", n_clusters=2, id_prefix="auto", labeler=labeler)

    assert {gate.metadata["label_source"] for gate in result.gates} == {"enhanced_assistant"}
    assert all(gate.name.startswith("Enhanced cluster") for gate in result.gates)
    assert all(not gate.enabled for gate in result.gates)


def test_ai_auto_gates_require_two_fluorescence_channels():
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=pd.DataFrame({"FSC-A": [1, 2, 3], "SSC-A": [1, 2, 3]}))
    sample.channels = summarize_channels(sample.events)

    result = suggest_ai_auto_gates(sample, x_channel="FSC-A", y_channel="SSC-A")

    assert result.gates == []
    assert "at least two" in result.warnings[0]
