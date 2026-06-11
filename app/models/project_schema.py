from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ProjectState:
    """Serializable project state. Raw event matrices are intentionally excluded."""

    project_title: str = "Ask Flow Workbench Project"
    app_version: str = "0.1.0"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sample_metadata: list[dict[str, Any]] = field(default_factory=list)
    file_references: list[dict[str, Any]] = field(default_factory=list)
    channel_role_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    transform_settings: dict[str, Any] = field(default_factory=dict)
    gate_definitions: list[dict[str, Any]] = field(default_factory=list)
    qc_results: list[dict[str, Any]] = field(default_factory=list)
    comparison_settings: dict[str, Any] = field(default_factory=dict)
    report_selections: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_title": self.project_title,
            "app_version": self.app_version,
            "created_at": self.created_at,
            "sample_metadata": self.sample_metadata,
            "file_references": self.file_references,
            "channel_role_overrides": self.channel_role_overrides,
            "transform_settings": self.transform_settings,
            "gate_definitions": self.gate_definitions,
            "qc_results": self.qc_results,
            "comparison_settings": self.comparison_settings,
            "report_selections": self.report_selections,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectState":
        return cls(
            project_title=payload.get("project_title", "Ask Flow Workbench Project"),
            app_version=payload.get("app_version", "0.1.0"),
            created_at=payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
            sample_metadata=list(payload.get("sample_metadata", [])),
            file_references=list(payload.get("file_references", [])),
            channel_role_overrides=dict(payload.get("channel_role_overrides", {})),
            transform_settings=dict(payload.get("transform_settings", {})),
            gate_definitions=list(payload.get("gate_definitions", [])),
            qc_results=list(payload.get("qc_results", [])),
            comparison_settings=dict(payload.get("comparison_settings", {})),
            report_selections=dict(payload.get("report_selections", {})),
        )
