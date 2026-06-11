import pandas as pd

from app.core.ask_flow import answer_question
from app.core.compensation import parse_spillover
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
