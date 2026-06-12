import numpy as np
import pandas as pd
import pytest

from app.core.gating import (
    apply_gate,
    apply_gate_tree,
    bi_range_gate,
    delete_gate,
    drawn_shape_gate,
    ellipse_gate,
    gate_to_table,
    histogram_range_gate,
    latest_drawn_shape,
    quadrant_gates,
    load_gates,
    rectangle_gate,
    rename_gate,
    review_current_view_gate,
    review_scatter_gate,
    save_gates,
    suggest_candidate_gates,
    toggle_gate_enabled,
)
from app.core.gate_colors import GATE_PALETTE, gate_color
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


def test_gate_table_includes_deterministic_display_color():
    gate = rectangle_gate("stable_gate", "Stable", "FSC-A", "SSC-A", 0, 1, 0, 1)

    rows = gate_to_table([gate])

    assert rows[0]["gate_color"] == gate_color("stable_gate")
    assert rows[0]["gate_color"] in GATE_PALETTE


def test_histogram_range_gate_membership():
    events = pd.DataFrame({"FL1-A": [10, 20, 30, 40]})
    gate = histogram_range_gate("h1", "positive", "FL1-A", 15, 35)

    mask = apply_gate(events, gate)

    assert mask.tolist() == [False, True, True, False]


def test_ellipse_gate_membership():
    events = pd.DataFrame({"FSC-A": [0, 1, 2, 3], "SSC-A": [0, 1, 2, 3]})
    gate = ellipse_gate("e1", "ellipse", "FSC-A", "SSC-A", center_x=1, center_y=1, radius_x=1.5, radius_y=1.5)

    mask = apply_gate(events, gate)

    assert mask.tolist() == [True, True, True, False]


def test_quadrant_gates_partition_events():
    events = pd.DataFrame({"FL1-A": [0, 0, 10, 10], "FL2-A": [0, 10, 0, 10]})
    gates = quadrant_gates("q", "CD4 CD8", "FL1-A", "FL2-A", x_threshold=5, y_threshold=5)

    masks = apply_gate_tree(events, gates)

    assert masks["q_upper_right"].tolist() == [False, False, False, True]
    assert masks["q_upper_left"].tolist() == [False, True, False, False]
    assert masks["q_lower_left"].tolist() == [True, False, False, False]
    assert masks["q_lower_right"].tolist() == [False, False, True, False]


def test_bi_range_gate_membership():
    events = pd.DataFrame({"FL1-A": [1, 5, 7], "FL2-A": [10, 20, 40]})
    gate = bi_range_gate("b1", "bi", "FL1-A", "FL2-A", 2, 6, 15, 25)

    mask = apply_gate(events, gate)

    assert mask.tolist() == [False, True, False]


def test_drawn_rectangle_shape_becomes_raw_review_gate():
    relayout = {"shapes": [{"type": "rect", "x0": 1.0, "x1": 2.0, "y0": 3.0, "y1": 4.0}]}

    gate, signature = drawn_shape_gate(
        relayout,
        gate_id="drawn",
        name="drawn gate",
        x_channel="FSC-A",
        y_channel="SSC-A",
        transform="raw",
    )

    assert gate is not None
    assert signature is not None
    assert gate.gate_type == "rectangle"
    assert gate.review_status == "review_needed"
    assert gate.bounds == {"x_min": 1.0, "x_max": 2.0, "y_min": 3.0, "y_max": 4.0}
    assert "drawn on plot" in gate.metadata["drawn_gate"]


def test_drawn_shape_inverts_display_transform_for_storage():
    relayout = {"shapes": [{"type": "rect", "x0": 0.0, "x1": 2.0, "y0": 0.0, "y1": 1.0}]}

    gate, _signature = drawn_shape_gate(
        relayout,
        gate_id="drawn",
        name="drawn gate",
        x_channel="FL1-A",
        y_channel="SSC-A",
        transform="safe_log10",
    )

    assert gate is not None
    assert gate.bounds["x_min"] == 1.0
    assert gate.bounds["x_max"] == 100.0
    assert gate.bounds["y_min"] == 1.0
    assert gate.bounds["y_max"] == 10.0


def test_drawn_shape_inverts_logicle_display_for_storage():
    from app.core.transforms import apply_transform

    raw_x = np.array([1000.0, 2000.0])
    raw_y = np.array([3000.0, 4000.0])
    display_x = apply_transform(raw_x, "logicle")
    display_y = apply_transform(raw_y, "logicle")
    relayout = {
        "shapes": [
            {
                "type": "rect",
                "x0": float(display_x[0]),
                "x1": float(display_x[1]),
                "y0": float(display_y[0]),
                "y1": float(display_y[1]),
            }
        ]
    }

    gate, _signature = drawn_shape_gate(
        relayout,
        gate_id="drawn",
        name="drawn gate",
        x_channel="FL1-A",
        y_channel="SSC-A",
        transform="logicle",
    )

    assert gate is not None
    assert gate.bounds["x_min"] == pytest.approx(1000.0)
    assert gate.bounds["x_max"] == pytest.approx(2000.0)
    assert gate.bounds["y_min"] == pytest.approx(3000.0)
    assert gate.bounds["y_max"] == pytest.approx(4000.0)


def test_drawn_shape_can_be_child_of_selected_parent():
    relayout = {"shapes": [{"type": "rect", "x0": 1.0, "x1": 2.0, "y0": 3.0, "y1": 4.0}]}

    gate, _signature = drawn_shape_gate(
        relayout,
        gate_id="child",
        name="drawn child",
        x_channel="FSC-A",
        y_channel="SSC-A",
        transform="raw",
        parent_id="parent",
    )

    assert gate is not None
    assert gate.parent_id == "parent"


def test_drawn_closed_path_shape_becomes_polygon_gate():
    relayout = {"shapes[0].type": "path", "shapes[0].path": "M 1,1 L 5,1 L 3,4 Z"}

    gate, signature = drawn_shape_gate(
        relayout,
        gate_id="poly",
        name="drawn polygon",
        x_channel="FSC-A",
        y_channel="SSC-A",
        transform="raw",
    )

    assert latest_drawn_shape(relayout)["type"] == "path"
    assert gate is not None
    assert signature is not None
    assert gate.gate_type == "polygon"
    assert gate.vertices == [(1.0, 1.0), (5.0, 1.0), (3.0, 4.0)]


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
    gate = GateDefinition("future1", "future", "future_gate", ["FSC-A", "SSC-A"])  # type: ignore[arg-type]

    masks = apply_gate_tree(events, [gate])

    np.testing.assert_array_equal(masks["future1"], np.array([False, False, False]))
    assert gate.metadata["mask_warning"] == "unsupported gate type: future_gate"


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


def test_review_scatter_gate_creates_enabled_editable_review_gate():
    events = pd.DataFrame(
        {
            "FSC-A": np.linspace(1, 1000, 500),
            "SSC-A": np.linspace(10, 2000, 500),
            "FITC-A": np.linspace(100, 500, 500),
        }
    )
    channels = [
        ChannelSummary(1, "FSC-A", role="fsc-a"),
        ChannelSummary(2, "SSC-A", role="ssc-a"),
        ChannelSummary(3, "FITC-A", role="fluorescence"),
    ]

    gate = review_scatter_gate(events, channels, "quick")

    assert gate is not None
    assert gate.enabled is True
    assert gate.candidate is False
    assert gate.user_defined is True
    assert gate.review_status == "review_needed"
    assert gate.channels == ["FSC-A", "SSC-A"]
    assert gate.bounds["x_min"] > 1
    assert "review/edit" in gate.metadata["review_gate_reason"]


def test_review_current_view_gate_uses_selected_channels():
    events = pd.DataFrame(
        {
            "FSC-A": np.linspace(1, 1000, 500),
            "FITC-A": np.linspace(100, 500, 500),
            "SSC-A": np.linspace(10, 2000, 500),
        }
    )

    gate = review_current_view_gate(events, "FSC-A", "FITC-A", "view")

    assert gate is not None
    assert gate.enabled is True
    assert gate.candidate is False
    assert gate.user_defined is True
    assert gate.review_status == "review_needed"
    assert gate.channels == ["FSC-A", "FITC-A"]
    assert gate.bounds["x_min"] > 1
    assert gate.bounds["y_max"] < 500
    assert "FSC-A/FITC-A" in gate.metadata["review_gate_reason"]


def test_gate_management_helpers_rename_toggle_and_delete():
    gate = rectangle_gate("g1", "old", "FSC-A", "SSC-A", 0, 1, 0, 1)
    gates = [gate]

    renamed = rename_gate(gates, "g1", "  main population  ")
    toggled = toggle_gate_enabled(gates, "g1")
    updated, deleted = delete_gate(gates, "g1")

    assert renamed is gate
    assert gate.name == "main population"
    assert toggled is gate
    assert gate.enabled is False
    assert deleted is True
    assert updated == []


def test_gate_management_helpers_ignore_missing_or_empty_inputs():
    gate = rectangle_gate("g1", "main", "FSC-A", "SSC-A", 0, 1, 0, 1)
    gates = [gate]

    assert rename_gate(gates, "g1", "  ") is None
    assert toggle_gate_enabled(gates, "missing") is None
    updated, deleted = delete_gate(gates, "missing")

    assert updated == gates
    assert deleted is False
