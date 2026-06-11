import numpy as np
import pandas as pd

from app.core.gating import apply_gate, apply_gate_tree, histogram_range_gate, load_gates, rectangle_gate, save_gates, suggest_candidate_gates
from app.models.channel import ChannelSummary
from app.models.gate import GateDefinition


def test_rectangle_gate_membership():
    events = pd.DataFrame({"FSC-A": [1, 5, 10], "SSC-A": [1, 5, 10]})
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 6, 0, 6)

    mask = apply_gate(events, gate)

    assert mask.tolist() == [True, True, False]


def test_gate_serialization(tmp_path):
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 6, 0, 6)
    path = tmp_path / "gates.json"

    save_gates([gate], path)
    loaded = load_gates(path)

    assert loaded[0].to_dict() == gate.to_dict()


def test_histogram_range_gate_membership():
    events = pd.DataFrame({"FL1-A": [10, 20, 30, 40]})
    gate = histogram_range_gate("h1", "positive", "FL1-A", 15, 35)

    mask = apply_gate(events, gate)

    assert mask.tolist() == [False, True, True, False]


def test_child_gate_is_constrained_even_when_listed_before_parent():
    events = pd.DataFrame({"FSC-A": [1, 2, 3, 4, 5], "SSC-A": [1, 2, 3, 4, 5]})
    parent = rectangle_gate("parent", "parent", "FSC-A", "SSC-A", 2, 4, 2, 4)
    child = rectangle_gate("child", "child", "FSC-A", "SSC-A", 1, 5, 1, 5, parent_id="parent")

    masks = apply_gate_tree(events, [child, parent])

    assert masks["parent"].tolist() == [False, True, True, True, False]
    assert masks["child"].tolist() == [False, True, True, True, False]


def test_child_gate_with_missing_parent_is_empty_and_warned():
    events = pd.DataFrame({"FSC-A": [1, 2, 3, 4, 5], "SSC-A": [1, 2, 3, 4, 5]})
    child = rectangle_gate("child", "child", "FSC-A", "SSC-A", 1, 5, 1, 5, parent_id="ghost")

    masks = apply_gate_tree(events, [child])

    assert not masks["child"].any()
    assert child.metadata["mask_warning"] == "missing parent gate: ghost"


def test_cyclic_gate_parents_are_empty_and_warned():
    events = pd.DataFrame({"FSC-A": [1, 2, 3], "SSC-A": [1, 2, 3]})
    gate_a = rectangle_gate("a", "a", "FSC-A", "SSC-A", 0, 3, 0, 3, parent_id="b")
    gate_b = rectangle_gate("b", "b", "FSC-A", "SSC-A", 0, 3, 0, 3, parent_id="a")

    masks = apply_gate_tree(events, [gate_a, gate_b])

    assert not masks["a"].any()
    assert not masks["b"].any()
    assert gate_a.metadata["mask_warning"] == "cyclic parent relationship"
    assert gate_b.metadata["mask_warning"] == "cyclic parent relationship"


def test_unknown_gate_type_is_empty_instead_of_crashing():
    events = pd.DataFrame({"FSC-A": [1, 2, 3], "SSC-A": [1, 2, 3]})
    gate = GateDefinition("q1", "quadrant", "quadrant", ["FSC-A", "SSC-A"])  # type: ignore[arg-type]

    masks = apply_gate_tree(events, [gate])

    np.testing.assert_array_equal(masks["q1"], np.array([False, False, False]))
    assert gate.metadata["mask_warning"] == "unsupported gate type: quadrant"


def test_candidate_gate_suggestions_are_disabled_review_needed_gates():
    events = pd.DataFrame(
        {
            "FSC-A": np.linspace(1, 1000, 500),
            "SSC-A": np.linspace(10, 2000, 500),
            "FSC-H": np.linspace(1, 900, 500),
        }
    )
    channels = [
        ChannelSummary(1, "FSC-A", role="fsc-a"),
        ChannelSummary(2, "SSC-A", role="ssc-a"),
        ChannelSummary(3, "FSC-H", role="fsc-h"),
    ]

    gates = suggest_candidate_gates(events, channels, id_prefix="s1")

    assert [gate.name for gate in gates] == ["candidate main FSC/SSC population", "candidate pulse-geometry singlet review"]
    assert all(gate.candidate for gate in gates)
    assert all(not gate.enabled for gate in gates)
    assert all(gate.review_status == "review_needed" for gate in gates)
    assert all("review" in gate.metadata["candidate_reason"] for gate in gates)
    masks = apply_gate_tree(events, gates)
    assert all(not mask.any() for mask in masks.values())
