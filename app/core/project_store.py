from __future__ import annotations

import json
from pathlib import Path

from app import __version__
from app.models.gate import GateDefinition
from app.models.project_schema import ProjectState
from app.models.qc_flag import QCFlag
from app.models.sample import SampleRecord


def save_project(project: ProjectState, path: str | Path) -> Path:
    """Save project metadata without embedding raw event matrices."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
    return target


def load_project(path: str | Path) -> ProjectState:
    """Load saved project metadata."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("project JSON must contain an object")
    return ProjectState.from_dict(payload)


def build_project_state(
    samples: list[SampleRecord],
    gates: list[GateDefinition],
    qc_flags: list[QCFlag],
    *,
    transform_settings: dict[str, object] | None = None,
    comparison_settings: dict[str, object] | None = None,
    report_selections: dict[str, object] | None = None,
    title: str = "Ask Flow Workbench Project",
) -> ProjectState:
    """Create a ProjectState without embedding raw event matrices."""
    return ProjectState(
        project_title=title,
        app_version=__version__,
        sample_metadata=[_sample_metadata(sample) for sample in samples],
        file_references=[_file_reference(sample) for sample in samples],
        transform_settings=transform_settings or {},
        gate_definitions=[gate.to_dict() for gate in gates],
        qc_results=[flag.to_dict() for flag in qc_flags],
        comparison_settings=comparison_settings or {},
        report_selections=report_selections or {},
    )


def gates_from_project(project: ProjectState) -> list[GateDefinition]:
    """Restore gate definitions from saved project metadata."""
    return [GateDefinition.from_dict(payload) for payload in project.gate_definitions]


def apply_project_sample_metadata(samples: list[SampleRecord], project: ProjectState) -> int:
    """Apply saved sample and channel annotations to currently loaded samples.

    Raw event matrices are still loaded from the uploaded FCS/CSV files. This
    function only restores local project annotations such as panel labels,
    conditions, replicates, notes, and channel role overrides.
    """
    saved = _saved_sample_lookup(project)
    applied = 0
    for sample in samples:
        payload = saved.get(sample.sample_id) or saved.get(sample.filename)
        if not payload:
            continue
        sample.condition = _optional_str(payload.get("condition"))
        sample.replicate = _optional_str(payload.get("replicate"))
        sample.control_type = _optional_str(payload.get("control_type"))
        sample.notes = _optional_str(payload.get("notes"))
        saved_channels = {
            str(channel.get("raw_name")): channel
            for channel in payload.get("channels", [])
            if isinstance(channel, dict) and channel.get("raw_name")
        }
        for channel in sample.channels:
            channel_payload = saved_channels.get(channel.raw_name)
            if not channel_payload:
                continue
            channel.display_label = _optional_str(channel_payload.get("display_label")) or channel.display_label
            channel.marker = _optional_str(channel_payload.get("marker")) or channel.marker
            channel.antibody = _optional_str(channel_payload.get("antibody")) or channel.antibody
            channel.fluorochrome = _optional_str(channel_payload.get("fluorochrome")) or channel.fluorochrome
            channel.role = _optional_str(channel_payload.get("role")) or channel.role
            applied += 1
    return applied


def _sample_metadata(sample: SampleRecord) -> dict[str, object]:
    return {
        "sample_id": sample.sample_id,
        "filename": sample.filename,
        "file_type": sample.file_type,
        "event_count": sample.event_count,
        "channel_count": sample.channel_count,
        "fcs_version": sample.fcs_version,
        "condition": sample.condition,
        "replicate": sample.replicate,
        "control_type": sample.control_type,
        "notes": sample.notes,
        "limitations": sample.limitations,
        "channels": [channel.to_dict() for channel in sample.channels],
    }


def _file_reference(sample: SampleRecord) -> dict[str, object]:
    return {
        "sample_id": sample.sample_id,
        "filename": sample.filename,
        "path": str(sample.path),
        "file_type": sample.file_type,
        "exists": Path(sample.path).exists(),
    }


def _saved_sample_lookup(project: ProjectState) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for payload in project.sample_metadata:
        sample_id = payload.get("sample_id")
        filename = payload.get("filename")
        if sample_id:
            lookup[str(sample_id)] = payload
        if filename:
            lookup[str(filename)] = payload
    return lookup


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
