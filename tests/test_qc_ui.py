from app.models.qc_flag import QCFlag
from app.ui.callbacks_qc import _review_lanes


def test_qc_review_lanes_group_flags_by_severity_and_sample():
    flags = [
        QCFlag(
            "s1",
            "warning",
            "LOW_EVENTS",
            "Low event count",
            "Rule-based warning for human review.",
            4000,
            5000,
            "Confirm event yield before gating.",
            ["gating", "comparison"],
        ),
        QCFlag(
            "s2",
            "info",
            "MISSING_TIME",
            "No Time channel detected",
            "Time stability plots are unavailable.",
            "missing",
            "Time channel present",
            "Review acquisition notes outside the app.",
            ["qc"],
        ),
    ]

    lanes = _review_lanes(flags, selected_sample="s1")
    text = " ".join(str(lane.to_plotly_json()) for lane in lanes)

    assert "warning" in text
    assert "Low event count" in text
    assert "Confirm event yield before gating." in text
    assert "No Time channel detected" not in text


def test_qc_review_lanes_empty_state_uses_review_language():
    lane = _review_lanes([], selected_sample=None)
    text = str(lane.to_plotly_json())

    assert "No QC review flags" in text
    assert "failed" not in text.lower()
