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
        if not isinstance(payload, dict):
            raise ValueError("project JSON must contain an object")
        return cls(
            project_title=payload.get("project_title", "Ask Flow Workbench Project"),
            app_version=payload.get("app_version", "0.1.0"),
            created_at=payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
            sample_metadata=_list_of_dicts(payload.get("sample_metadata", []), "sample_metadata"),
            file_references=_list_of_dicts(payload.get("file_references", []), "file_references"),
            channel_role_overrides=_dict(payload.get("channel_role_overrides", {}), "channel_role_overrides"),
            transform_settings=_dict(payload.get("transform_settings", {}), "transform_settings"),
            gate_definitions=_list_of_dicts(payload.get("gate_definitions", []), "gate_definitions"),
            qc_results=_list_of_dicts(payload.get("qc_results", []), "qc_results"),
            comparison_settings=_dict(payload.get("comparison_settings", {}), "comparison_settings"),
            report_selections=_dict(payload.get("report_selections", {}), "report_selections"),
        )


def _dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return dict(value)


def _list_of_dicts(value: Any, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name} must contain objects")
    return [dict(item) for item in value]
