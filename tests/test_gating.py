import pandas as pd

from app.core.gating import apply_gate, histogram_range_gate, load_gates, rectangle_gate, save_gates


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
