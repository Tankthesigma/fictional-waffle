from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app import __version__


@dataclass(slots=True)
class AnalysisTemplate:
    """Reusable analysis setup without raw event data or file references."""

    template_name: str = "Ask Flow Analysis Template"
    app_version: str = __version__
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    plot_settings: dict[str, Any] = field(default_factory=dict)
    gate_definitions: list[dict[str, Any]] = field(default_factory=list)
    comparison_settings: dict[str, Any] = field(default_factory=dict)
    report_selections: dict[str, Any] = field(default_factory=dict)
    channel_annotations: list[dict[str, Any]] = field(default_factory=list)
    notes: str = "Reusable post-acquisition analysis setup. Raw event matrices are not embedded."

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_name": self.template_name,
            "app_version": self.app_version,
            "created_at": self.created_at,
            "plot_settings": self.plot_settings,
            "gate_definitions": self.gate_definitions,
            "comparison_settings": self.comparison_settings,
            "report_selections": self.report_selections,
            "channel_annotations": self.channel_annotations,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnalysisTemplate":
        if not isinstance(payload, dict):
            raise ValueError("analysis template JSON must contain an object")
        return cls(
            template_name=str(payload.get("template_name") or "Ask Flow Analysis Template"),
            app_version=str(payload.get("app_version") or __version__),
            created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()),
            plot_settings=_dict(payload.get("plot_settings", {}), "plot_settings"),
            gate_definitions=_list_of_dicts(payload.get("gate_definitions", []), "gate_definitions"),
            comparison_settings=_dict(payload.get("comparison_settings", {}), "comparison_settings"),
            report_selections=_dict(payload.get("report_selections", {}), "report_selections"),
            channel_annotations=_list_of_dicts(payload.get("channel_annotations", []), "channel_annotations"),
            notes=str(payload.get("notes") or "Reusable post-acquisition analysis setup. Raw event matrices are not embedded."),
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
