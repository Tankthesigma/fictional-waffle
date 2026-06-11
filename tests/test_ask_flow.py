import pandas as pd

from app.core.ask_flow import analysis_briefing, analysis_plan, answer_question
from app.core.compensation import parse_spillover
from app.models.channel import ChannelSummary
from app.models.gate import GateDefinition
from app.models.qc_flag import QCFlag
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


def test_analysis_briefing_summarizes_context_without_claims():
    sample = SampleRecord(
        "s1",
        "s1.csv",
        path="unused.csv",
        file_type="csv",
        events=pd.DataFrame({"FSC-A": [1, 2], "FL1-A": [10, 20]}),
        channels=[
            ChannelSummary(1, "FSC-A", role="fsc-a"),
            ChannelSummary(2, "FL1-A", role="fluorescence", marker="CD3", fluorochrome="FITC"),
        ],
    )
    gate = GateDefinition("g1", "Current view review gate", "rectangle", ["FSC-A", "FL1-A"], review_status="review_needed")
    flag = QCFlag(
        sample_id="s1",
        severity="warning",
        code="POSSIBLE_HIGH_CLIPPING",
        title="Possible high-end clipping",
        explanation="review distribution",
        metric_value=2.0,
        threshold=1.0,
        suggested_check="Inspect histogram",
        affects=["plotting"],
        channel="FL1-A",
    )

    cards = analysis_briefing(
        sample,
        x_channel="FSC-A",
        y_channel="FL1-A",
        gates=[gate],
        qc_flags=[flag],
        comparison_rows=[{"channel": "FL1-A", "median_difference": 5.0, "notes": "exploratory only"}],
    )
    text = " ".join(f"{card['title']} {card['body']} {card['detail']}" for card in cards)

    assert cards[0]["title"] == "Active Context"
    assert "s1: 2 events, 2 channels" in text
    assert "FSC-A x CD3 FITC (FL1-A)" in text
    assert "Top review flag: Possible high-end clipping on FL1-A" in text
    assert "1 enabled user/review gate(s)" in text
    assert "FL1-A is higher in treated medians by +5" in text
    assert "does not infer cell identity, diagnosis" in text
    assert "biologically correct" in text


def test_analysis_briefing_empty_state_is_waiting():
    cards = analysis_briefing(None)

    assert cards == [
        {
            "status": "waiting",
            "title": "No Active Sample",
            "body": "Upload FCS or event-level CSV files to generate a local analysis briefing.",
            "detail": "Ask Flow stays local and deterministic.",
        }
    ]


def test_analysis_plan_guides_next_steps_without_overclaiming():
    sample = SampleRecord(
        "s1",
        "s1.csv",
        path="unused.csv",
        file_type="csv",
        events=pd.DataFrame({"FSC-A": [1, 2], "SSC-A": [1, 2], "FL1-A": [10, 20]}),
        channels=[ChannelSummary(1, "FSC-A", role="fsc-a"), ChannelSummary(2, "SSC-A", role="ssc-a"), ChannelSummary(3, "FL1-A", role="fluorescence")],
    )
    flag = QCFlag(
        sample_id="s1",
        severity="warning",
        code="POSSIBLE_HIGH_CLIPPING",
        title="Possible high-end clipping",
        explanation="review distribution",
        metric_value=2.0,
        threshold=1.0,
        suggested_check="Inspect histogram",
        affects=["plotting"],
        channel="FL1-A",
    )

    plan = analysis_plan(sample, qc_flags=[flag])
    answer = answer_question("plan the analysis", sample, qc_flags=[flag])
    text = " ".join(f"{row['title']} {row['body']} {row['detail']}" for row in plan)

    assert "Review Acquisition Shape" in text
    assert "Resolve QC Review Items" in text
    assert "Create A Review Gate" in text
    assert "Add Group Labels" in text
    assert "Suggested analysis plan" in answer
