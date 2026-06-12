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
    from app.ui.callbacks_ask_flow import _requests_auto_gate

    assert _requests_auto_gate("make clusterns")
    assert _requests_auto_gate("do clusters")
    assert not _requests_auto_gate("so everything")


def _sample(sample_id: str = "s1") -> SampleRecord:
    frame = pd.DataFrame({"FSC-A": [1, 2], "SSC-A": [1, 4], "FL1-A": [10, 20]})
    sample = SampleRecord(sample_id, f"{sample_id}.csv", path="unused.csv", file_type="csv", events=frame)
    sample.channels = [
        ChannelSummary(1, "FSC-A", role="fsc-a"),
        ChannelSummary(2, "SSC-A", role="ssc-a"),
        ChannelSummary(3, "FL1-A", role="fluorescence", marker="CD3", fluorochrome="FITC"),
    ]
    return sample
