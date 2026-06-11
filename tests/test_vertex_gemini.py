import pandas as pd

from app.core.vertex_gemini import answer_with_gemini, vertex_enabled, vertex_status
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
