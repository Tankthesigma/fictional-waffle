from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.analysis_template import AnalysisTemplate
from app.models.gate import GateDefinition
from app.models.sample import SampleRecord


def build_analysis_template(
    samples: list[SampleRecord],
    gates: list[GateDefinition],
    *,
    plot_settings: dict[str, Any] | None = None,
    comparison_settings: dict[str, Any] | None = None,
    report_selections: dict[str, Any] | None = None,
    template_name: str = "Ask Flow Analysis Template",
) -> AnalysisTemplate:
    """Create a reusable analysis setup without raw events or file references."""
    return AnalysisTemplate(
        template_name=template_name,
        plot_settings=plot_settings or {},
        gate_definitions=[gate.to_dict() for gate in gates],
        comparison_settings=comparison_settings or {},
        report_selections=report_selections or {},
        channel_annotations=_channel_annotations(samples),
    )


def save_analysis_template(template: AnalysisTemplate, path: str | Path) -> Path:
    """Save a reusable analysis template JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(template.to_dict(), indent=2), encoding="utf-8")
    return target


def load_analysis_template(path: str | Path) -> AnalysisTemplate:
    """Load a reusable analysis template JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("analysis template JSON must contain an object")
    return AnalysisTemplate.from_dict(payload)


def gates_from_template(template: AnalysisTemplate) -> list[GateDefinition]:
    """Restore gate definitions from a template."""
    return [GateDefinition.from_dict(payload) for payload in template.gate_definitions]


def apply_template_channel_annotations(samples: list[SampleRecord], template: AnalysisTemplate) -> int:
    """Apply reusable channel labels/roles by raw channel name."""
    annotations = {
        str(item.get("raw_name")): item
        for item in template.channel_annotations
        if isinstance(item, dict) and item.get("raw_name")
    }
    applied = 0
    for sample in samples:
        for channel in sample.channels:
            payload = annotations.get(channel.raw_name)
            if not payload:
                continue
            channel.display_label = _optional_str(payload.get("display_label")) or channel.display_label
            channel.marker = _optional_str(payload.get("marker")) or channel.marker
            channel.antibody = _optional_str(payload.get("antibody")) or channel.antibody
            channel.fluorochrome = _optional_str(payload.get("fluorochrome")) or channel.fluorochrome
            channel.role = _optional_str(payload.get("role")) or channel.role
            applied += 1
    return applied


def _channel_annotations(samples: list[SampleRecord]) -> list[dict[str, Any]]:
    by_raw: dict[str, dict[str, Any]] = {}
    for sample in samples:
        for channel in sample.channels:
            if channel.raw_name not in by_raw or _has_context(channel):
                by_raw[channel.raw_name] = {
                    "raw_name": channel.raw_name,
                    "display_label": channel.display_label,
                    "marker": channel.marker,
                    "antibody": channel.antibody,
                    "fluorochrome": channel.fluorochrome,
                    "role": channel.role,
                }
    return list(by_raw.values())


def _has_context(channel) -> bool:
    return bool(channel.display_label or channel.marker or channel.antibody or channel.fluorochrome)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
