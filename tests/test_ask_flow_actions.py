import pandas as pd

from app.core.ask_flow_actions import plan_actions
from app.models.channel import ChannelSummary
from app.models.sample import SampleRecord


def test_ask_flow_plans_safe_plot_actions():
    sample = _sample()

    plan = plan_actions("plot FL1-A vs SSC-A as density with arcsinh and show 100000 events", [sample], sample)

    assert plan.updates["x_channel"] == "FL1-A"
    assert plan.updates["y_channel"] == "SSC-A"
    assert plan.updates["plot_mode"] == "density"
    assert plan.updates["transform"] == "arcsinh"
    assert plan.updates["max_events"] == 100_000
    assert "Set scatter axes to FL1-A vs SSC-A." in plan.messages


def test_ask_flow_plans_histogram_action_from_marker_label():
    sample = _sample()

    plan = plan_actions("show histogram of CD3", [sample], sample)

    assert plan.updates["hist_channel"] == "FL1-A"
    assert plan.messages == ["Set histogram channel to FL1-A."]


def test_ask_flow_can_select_sample_by_id():
    control = _sample("control")
    treated = _sample("treated")

    plan = plan_actions("switch to treated", [control, treated], control)

    assert plan.updates["sample_id"] == "treated"


def test_ask_flow_plans_safe_tab_navigation():
    sample = _sample()

    plan = plan_actions("show QC for this sample", [sample], sample)

    assert plan.updates["tab"] == "qc"
    assert "Opened the QC workspace." in plan.messages


def test_ask_flow_understands_casual_graph_command():
    sample = _sample()

    plan = plan_actions("do graph", [sample], sample)

    assert plan.updates["tab"] == "explore"
    assert "Opened the Explore workspace." in plan.messages


def test_ask_flow_understands_messy_cluster_command():
    from app.ui.callbacks_ask_flow import _requests_auto_gate, _requests_candidate_gates, _requests_current_view_gate, _requests_histogram_gate, _requests_scatter_review_gate

    assert _requests_auto_gate("make clusterns")
    assert _requests_auto_gate("do clusters")
    assert _requests_current_view_gate("make a gate on this plot")
    assert _requests_scatter_review_gate("make main population fsc ssc gate")
    assert _requests_histogram_gate("make positive histogram gate")
    assert _requests_candidate_gates("suggest candidate gates")
    assert not _requests_auto_gate("so everything")


def test_ask_flow_can_create_review_needed_current_view_gate():
    from app.core.session_store import WorkbenchSession
    from app.ui.callbacks_ask_flow import _run_current_view_gate_from_chat

    sample = _sample()
    session = WorkbenchSession(samples={sample.sample_id: sample})

    status, outputs = _run_current_view_gate_from_chat(session, sample, "FSC-A", "SSC-A", [])

    assert "Added editable review-needed current-view gate" in status
    assert len(session.gates) == 1
    assert session.gates[0].channels == ["FSC-A", "SSC-A"]
    assert session.gates[0].review_status == "review_needed"
    assert outputs[5] == session.gates[0].gate_id


def test_ask_flow_can_create_review_needed_histogram_gate():
    from app.core.session_store import WorkbenchSession
    from app.ui.callbacks_ask_flow import _run_histogram_gate_from_chat

    sample = _sample()
    session = WorkbenchSession(samples={sample.sample_id: sample})

    status, outputs = _run_histogram_gate_from_chat(session, sample, "FL1-A", [])

    assert "Added editable review-needed histogram gate" in status
    assert len(session.gates) == 1
    assert session.gates[0].gate_type == "histogram_range"
    assert session.gates[0].channels == ["FL1-A"]
    assert session.gates[0].review_status == "review_needed"
    assert outputs[5] == session.gates[0].gate_id


def _sample(sample_id: str = "s1") -> SampleRecord:
    frame = pd.DataFrame(
        {
            "FSC-A": list(range(1, 151)),
            "SSC-A": list(range(101, 251)),
            "FL1-A": list(range(201, 351)),
        }
    )
    sample = SampleRecord(sample_id, f"{sample_id}.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = [
        ChannelSummary(1, "FSC-A", role="fsc-a"),
        ChannelSummary(2, "SSC-A", role="ssc-a"),
        ChannelSummary(3, "FL1-A", role="fluorescence", marker="CD3", fluorochrome="FITC"),
    ]
    return sample
