from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


Severity = Literal["info", "warning", "severe"]


@dataclass(slots=True)
class QCFlag:
    """Rule-based QC flag that explains why review is needed."""

    sample_id: str
    severity: Severity
    code: str
    title: str
    explanation: str
    metric_value: Any
    threshold: Any
    suggested_check: str
    affects: list[str]
    channel: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "severity": self.severity,
            "code": self.code,
            "title": self.title,
            "explanation": self.explanation,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "suggested_check": self.suggested_check,
            "affects": ", ".join(self.affects),
            "channel": self.channel or "",
        }
