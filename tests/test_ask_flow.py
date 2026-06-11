import pandas as pd

from app.core.ask_flow import answer_question
from app.core.compensation import parse_spillover
from app.models.channel import ChannelSummary
from app.models.gate import GateDefinition
from app.models.sample import SampleRecord


def test_ask_flow_answers_compensation_locally():
    sample = SampleRecord(
        "s1",
        "s1.fcs",
        path="unused.fcs",
        file_type="fcs",
        events=pd.DataFrame({"FL1-A": [1.0]}),
        spillover=parse_spillover({"$SPILL": "1,FL1-A,1"}),
        compensated_events=pd.DataFrame({"FL1-A": [1.0]}),
    )

    answer = answer_question("is compensation applied?", sample)

    assert "Metadata compensation available" in answer
    assert "raw exported events remain untouched" in answer


def test_ask_flow_uses_panel_labels_for_plot_answers():
    sample = SampleRecord(
        "s1",
        "s1.csv",
        path="unused.csv",
        file_type="csv",
        events=pd.DataFrame({"FSC-A": [1, 2], "FL1-A": [10, 20]}),
        channels=[
            ChannelSummary(1, "FSC-A", role="fsc-a"),
            ChannelSummary(2, "FL1-A", role="fluorescence", marker="CD3", antibody="UCHT1", fluorochrome="FITC"),
        ],
    )

    answer = answer_question("what does this plot show?", sample, x_channel="FSC-A", y_channel="FL1-A")

    assert "FSC-A versus CD3 FITC (FL1-A)" in answer
    assert "fluorescence, marker CD3, antibody UCHT1" in answer


def test_ask_flow_distinguishes_candidate_gates():
    sample = SampleRecord(
        "s1",
        "s1.csv",
        path="unused.csv",
        file_type="csv",
        events=pd.DataFrame({"FSC-A": [1, 2], "SSC-A": [1, 2]}),
        channels=[ChannelSummary(1, "FSC-A", role="fsc-a"), ChannelSummary(2, "SSC-A", role="ssc-a")],
    )
    candidate = GateDefinition(
        "c1",
        "candidate main",
        "rectangle",
        ["FSC-A", "SSC-A"],
        enabled=False,
        candidate=True,
        review_status="review_needed",
    )

    answer = answer_question("explain this gate", sample, gates=[candidate])

    assert "candidate review-needed gates: 1" in answer
    assert "suggestions only until accepted or edited" in answer


def test_ask_flow_uses_comparison_summary():
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=pd.DataFrame({"FL1-A": [1, 2]}))

    answer = answer_question(
        "how do treated samples compare with controls?",
        sample,
        comparison_rows=[
            {"channel": "FL1-A", "median_difference": 4.0, "notes": "exploratory only"},
            {
                "channel": "PE-A",
                "median_difference": -2.0,
                "notes": "fold-change not computed for negative or near-zero medians; use median difference",
            },
        ],
    )

    assert "Strongest Increase: +4" in answer
    assert "Guarded Fold-Changes: 1" in answer
