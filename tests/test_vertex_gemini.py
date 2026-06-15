import pandas as pd

from app.core.vertex_gemini import _parse_cluster_labels, _prompt, answer_with_gemini, vertex_enabled, vertex_status
from app.models.sample import SampleRecord


def test_vertex_gemini_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ASK_FLOW_CLOUD_ASSISTANT_ENABLED", raising=False)
    monkeypatch.delenv("ASK_FLOW_VERTEX_ENABLED", raising=False)
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=pd.DataFrame({"FL1-A": [1]}))

    answer = answer_with_gemini("hello", sample, fallback="local answer")

    assert vertex_enabled() is False
    assert answer.text == "local answer"
    assert answer.used_vertex is False
    assert "Assistant: local mode" in vertex_status()


def test_vertex_gemini_requires_project_when_enabled(monkeypatch):
    monkeypatch.setenv("ASK_FLOW_CLOUD_ASSISTANT_ENABLED", "1")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT_ID", raising=False)
    sample = SampleRecord("s1", "s1.csv", path="unused.csv", file_type="csv", events=pd.DataFrame({"FL1-A": [1]}))

    answer = answer_with_gemini("hello", sample, fallback="local answer")

    assert answer.text == "local answer"
    assert answer.used_vertex is False
    assert "GOOGLE_CLOUD_PROJECT is not set" in answer.status


def test_cloud_assistant_status_hides_provider_details(monkeypatch):
    monkeypatch.setenv("ASK_FLOW_CLOUD_ASSISTANT_ENABLED", "1")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")

    status = vertex_status()

    assert "Assistant: enhanced mode enabled" in status
    assert "Gemini" not in status
    assert "Vertex" not in status


def test_cloud_prompt_allows_general_questions_without_sample():
    prompt = _prompt(
        "who is the president of america?",
        None,
        x_channel=None,
        y_channel=None,
        gates=[],
        qc_flags=[],
        comparison_rows=[],
        action_messages=[],
    )

    assert "general_question_mode" in prompt
    assert "current_date" in prompt
    assert "You may answer ordinary general-knowledge" in prompt
    assert "Use current_date for time-sensitive general questions" in prompt
    assert "upload or select a sample first" in prompt


def test_parse_cluster_labels_keeps_review_language_and_rejects_bad_claims():
    labels = _parse_cluster_labels('[{"cluster": 2, "label": "CD3 high"}, {"cluster": 3, "label": "confirmed disease"}]')

    assert labels[2] == "CD3 high review"
    assert labels[3] == "Cluster review: marker-pattern review needed"
