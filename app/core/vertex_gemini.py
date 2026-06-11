from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from app.core.ask_flow import FORBIDDEN_NOTICE
from app.core.compensation import compensation_status
from app.core.qc import qc_summary
from app.models.gate import GateDefinition
from app.models.qc_flag import QCFlag
from app.models.sample import SampleRecord


DEFAULT_VERTEX_MODEL = "gemini-3.5-flash"


@dataclass(slots=True)
class GeminiAnswer:
    """Optional Vertex/Gemini response plus status details."""

    text: str
    used_vertex: bool
    status: str


def vertex_enabled() -> bool:
    """Return whether Ask Flow should attempt Vertex/Gemini calls."""
    value = os.getenv("ASK_FLOW_VERTEX_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on", "auto"}


def vertex_status() -> str:
    """Human-readable Vertex/Gemini runtime status."""
    if not vertex_enabled():
        return "Vertex Gemini: off. Set ASK_FLOW_VERTEX_ENABLED=1 to enable cloud answers."
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    model = os.getenv("ASK_FLOW_GEMINI_MODEL", DEFAULT_VERTEX_MODEL)
    if not project:
        return "Vertex Gemini: enabled, but GOOGLE_CLOUD_PROJECT is not set."
    return f"Vertex Gemini: enabled ({model}, project {project}, location {location})."


def answer_with_gemini(
    question: str,
    sample: SampleRecord | None,
    *,
    fallback: str,
    x_channel: str | None = None,
    y_channel: str | None = None,
    gates: list[GateDefinition] | None = None,
    qc_flags: list[QCFlag] | None = None,
    comparison_rows: list[dict[str, object]] | None = None,
    action_messages: list[str] | None = None,
) -> GeminiAnswer:
    """Answer with Vertex/Gemini when explicitly enabled, otherwise return fallback."""
    if not vertex_enabled():
        return GeminiAnswer(fallback, used_vertex=False, status=vertex_status())
    try:
        from google import genai
        from google.genai.types import HttpOptions
    except Exception as exc:
        return GeminiAnswer(fallback, used_vertex=False, status=f"Vertex Gemini unavailable: google-genai is not installed ({exc}).")

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    model = os.getenv("ASK_FLOW_GEMINI_MODEL", DEFAULT_VERTEX_MODEL)
    if not project:
        return GeminiAnswer(fallback, used_vertex=False, status="Vertex Gemini unavailable: GOOGLE_CLOUD_PROJECT is not set.")

    try:
        client = genai.Client(vertexai=True, project=project, location=location, http_options=HttpOptions(api_version="v1"))
        response = client.models.generate_content(
            model=model,
            contents=_prompt(
                question,
                sample,
                x_channel=x_channel,
                y_channel=y_channel,
                gates=gates or [],
                qc_flags=qc_flags or [],
                comparison_rows=comparison_rows or [],
                action_messages=action_messages or [],
            ),
        )
        text = (getattr(response, "text", "") or "").strip()
        if not text:
            return GeminiAnswer(fallback, used_vertex=False, status=f"Vertex Gemini returned an empty answer from {model}; local answer shown.")
        return GeminiAnswer(text, used_vertex=True, status=f"Vertex Gemini answered with {model}.")
    except Exception as exc:
        return GeminiAnswer(fallback, used_vertex=False, status=f"Vertex Gemini unavailable: {exc}. Local answer shown.")


def _prompt(
    question: str,
    sample: SampleRecord | None,
    *,
    x_channel: str | None,
    y_channel: str | None,
    gates: list[GateDefinition],
    qc_flags: list[QCFlag],
    comparison_rows: list[dict[str, object]],
    action_messages: list[str],
) -> str:
    context = {
        "app": "Ask Flow Workbench",
        "scope": "post-acquisition FCS/CSV analysis only; no instrument control",
        "question": question,
        "actions_already_applied": action_messages,
        "sample": _sample_context(sample, x_channel, y_channel),
        "qc_summary": qc_summary(qc_flags),
        "qc_flags": [flag.to_dict() for flag in qc_flags[:20]],
        "gates": [_gate_context(gate) for gate in gates[:20]],
        "comparison_rows": comparison_rows[:30],
        "forbidden_notice": FORBIDDEN_NOTICE,
    }
    return (
        "You are Ask Flow inside a local flow cytometry analysis workbench. "
        "Answer the user's question using only the provided context. Be concise, practical, and plain-English. "
        "Never infer cell identity unless marker meaning was provided. Never diagnose disease. Never claim gates are correct. "
        "Never suggest cytometer operation, acquisition settings, lasers, fluidics, cleaning, maintenance, firmware, drivers, or hardware control. "
        "Call candidate gates review-needed. Label comparison statistics exploratory. "
        "If the user asks for a task, describe only the safe app action already applied in actions_already_applied; do not invent additional execution. "
        "Context JSON:\n"
        + json.dumps(context, default=str)
    )


def _sample_context(sample: SampleRecord | None, x_channel: str | None, y_channel: str | None) -> dict[str, Any]:
    if sample is None:
        return {}
    return {
        "sample_id": sample.sample_id,
        "filename": sample.filename,
        "event_count": sample.event_count,
        "channel_count": sample.channel_count,
        "condition": sample.condition,
        "replicate": sample.replicate,
        "control_type": sample.control_type,
        "selected_x_channel": x_channel,
        "selected_y_channel": y_channel,
        "compensation_status": compensation_status(sample),
        "channels": [
            {
                "raw_name": channel.raw_name,
                "label": channel.label,
                "role": channel.role,
                "marker": channel.marker,
                "fluorochrome": channel.fluorochrome,
                "median": channel.median,
                "p1": channel.p1,
                "p99": channel.p99,
            }
            for channel in sample.channels[:80]
        ],
    }


def _gate_context(gate: GateDefinition) -> dict[str, Any]:
    return {
        "gate_id": gate.gate_id,
        "name": gate.name,
        "type": gate.gate_type,
        "channels": gate.channels,
        "parent_id": gate.parent_id,
        "enabled": gate.enabled,
        "candidate": gate.candidate,
        "review_status": gate.review_status,
        "metadata": gate.metadata,
    }
