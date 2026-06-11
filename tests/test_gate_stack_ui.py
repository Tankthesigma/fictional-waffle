from app.core.gating import rectangle_gate
from app.ui.callbacks_gating import _gate_stack_cards


def test_gate_stack_cards_show_population_counts_and_review_state():
    gate = rectangle_gate("g1", "Main population", "FSC-A", "SSC-A", 0, 1, 0, 1)
    stats = [
        {
            "gate_id": "g1",
            "event_count": 1250,
            "percent_total": 62.5,
            "percent_parent": 62.5,
        }
    ]

    cards = _gate_stack_cards([gate], stats)
    text = " ".join(str(card.to_plotly_json()) for card in cards)

    assert "Main population" in text
    assert "active" in text
    assert "1250 events" in text
    assert "62.5% total" in text


def test_gate_stack_cards_surface_candidate_and_mask_warnings():
    gate = rectangle_gate("candidate", "Candidate singlet review", "FSC-A", "FSC-H", 0, 1, 0, 1)
    gate.candidate = True
    gate.enabled = False
    gate.metadata["mask_warning"] = "missing parent gate: main"

    cards = _gate_stack_cards([gate], [])
    text = " ".join(str(card.to_plotly_json()) for card in cards)

    assert "candidate review needed" in text
    assert "missing parent gate: main" in text
    assert "n/a events" in text
