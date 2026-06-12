from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app import __version__
from app.core.compensation import event_view
from app.core.gating import apply_gate_tree, find_gate
from app.models.gate import GateDefinition
from app.models.sample import SampleRecord


@dataclass(frozen=True, slots=True)
class PopulationExportResult:
    """Result of a gated population export."""

    path: Path
    event_count: int
    view_name: str


def export_gated_population_csv(
    sample: SampleRecord,
    gates: list[GateDefinition],
    gate_id: str,
    output_dir: str | Path,
    *,
    use_compensation: bool = False,
) -> PopulationExportResult:
    """Export one gated population to CSV."""
    gate, events, mask, view_name = _gated_events(sample, gates, gate_id, use_compensation=use_compensation)
    target = _population_path(output_dir, sample, gate, view_name, "csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    events.loc[mask].to_csv(target, index=False)
    return PopulationExportResult(target, int(mask.sum()), view_name)


def export_gated_population_fcs(
    sample: SampleRecord,
    gates: list[GateDefinition],
    gate_id: str,
    output_dir: str | Path,
    *,
    use_compensation: bool = False,
) -> PopulationExportResult:
    """Export one gated population to an analysis FCS file using FlowIO."""
    gate, events, mask, view_name = _gated_events(sample, gates, gate_id, use_compensation=use_compensation)
    if int(mask.sum()) == 0:
        raise ValueError("this gate has no events to export as FCS")
    frame = _numeric_events(events.loc[mask])
    if frame.empty and int(mask.sum()) > 0:
        raise ValueError("gated population has no numeric event columns to export as FCS")
    target = _population_path(output_dir, sample, gate, view_name, "fcs")
    metadata = _export_metadata(sample, gate, int(len(events)), int(mask.sum()), view_name, frame)
    _write_fcs(target, frame, sample, metadata)
    return PopulationExportResult(target, int(mask.sum()), view_name)


def export_events_fcs(
    events: pd.DataFrame,
    path: str | Path,
    *,
    sample: SampleRecord,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Write a complete event matrix to FCS."""
    frame = _numeric_events(events)
    if frame.empty and len(events) > 0:
        raise ValueError("event table has no numeric columns to export as FCS")
    target = Path(path)
    export_metadata = _channel_range_metadata(frame)
    export_metadata.update({str(key): str(value) for key, value in (metadata or {}).items() if value is not None})
    _write_fcs(target, frame, sample, export_metadata)
    return target


def _gated_events(
    sample: SampleRecord,
    gates: list[GateDefinition],
    gate_id: str,
    *,
    use_compensation: bool,
) -> tuple[GateDefinition, pd.DataFrame, np.ndarray, str]:
    gate = find_gate(gates, gate_id)
    if gate is None:
        raise ValueError("select a gate before exporting a gated population")
    events = event_view(sample, use_compensation)
    view_name = "metadata_compensated" if use_compensation and sample.compensated_events is not None else "raw"
    compatible = [item for item in gates if item.metadata.get("event_view", "raw") == view_name]
    masks = apply_gate_tree(events, compatible)
    mask = masks.get(gate.gate_id)
    if mask is None:
        raise ValueError("selected gate is not compatible with the active raw/compensated view")
    return gate, events, mask, view_name


def _write_fcs(target: Path, frame: pd.DataFrame, sample: SampleRecord, metadata: dict[str, Any]) -> None:
    try:
        from flowio import create_fcs  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency failure path
        raise RuntimeError("FlowIO create_fcs is required for FCS export") from exc

    target.parent.mkdir(parents=True, exist_ok=True)
    channel_names = [str(column) for column in frame.columns]
    opt_channel_names = [_channel_label(sample, channel) for channel in channel_names]
    with target.open("wb") as handle:
        create_fcs(
            handle,
            frame.to_numpy(dtype=np.float32).ravel(order="C").tolist(),
            channel_names,
            opt_channel_names=opt_channel_names,
            metadata_dict={str(key): str(value) for key, value in metadata.items() if value is not None},
        )


def _numeric_events(events: pd.DataFrame) -> pd.DataFrame:
    numeric = events.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    numeric = numeric.dropna(axis=1, how="all")
    return numeric.fillna(0.0)


def _export_metadata(sample: SampleRecord, gate: GateDefinition, source_count: int, exported_count: int, view_name: str, frame: pd.DataFrame) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "AFW_EXPORT_TYPE": "gated_population",
        "AFW_APP_VERSION": __version__,
        "AFW_SOURCE_FILE": sample.filename,
        "AFW_SAMPLE_ID": sample.sample_id,
        "AFW_GATE_ID": gate.gate_id,
        "AFW_GATE_NAME": gate.name,
        "AFW_PARENT_GATE": gate.parent_id or "total",
        "AFW_VIEW": view_name,
        "AFW_COMPENSATED": "true" if view_name != "raw" else "false",
        "AFW_SOURCE_EVENT_COUNT": source_count,
        "AFW_EXPORTED_EVENT_COUNT": exported_count,
        "AFW_GENERATED_AT": datetime.now().isoformat(timespec="seconds"),
        "AFW_DISCLAIMER": "Post-acquisition analysis export; not an instrument acquisition file.",
    }
    metadata.update(_channel_range_metadata(frame))
    return metadata


def _channel_range_metadata(frame: pd.DataFrame) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for index, column in enumerate(frame.columns, start=1):
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        max_abs = float(np.max(np.abs(finite))) if finite.size else 1.0
        metadata[f"$P{index}R"] = _range_ceiling(max_abs)
    return metadata


def _range_ceiling(value: float) -> int:
    if not math.isfinite(value) or value <= 0:
        return 1
    return int(2 ** math.ceil(math.log2(max(value, 1.0))))


def _population_path(output_dir: str | Path, sample: SampleRecord, gate: GateDefinition, view_name: str, suffix: str) -> Path:
    view = "COMPENSATED" if view_name != "raw" else "RAW"
    filename = f"{_safe_name(sample.sample_id)}__{_safe_name(gate.name)}__{view}.{suffix}"
    return Path(output_dir) / filename


def _channel_label(sample: SampleRecord, raw_name: str) -> str:
    for channel in sample.channels:
        if channel.raw_name == raw_name:
            return channel.label
    return raw_name


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value)).strip("_")
    return safe or "export"
