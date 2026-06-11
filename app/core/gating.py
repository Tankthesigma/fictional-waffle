from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.channel_inference import best_scatter_pair
from app.models.channel import ChannelSummary
from app.models.gate import GateDefinition


SUPPORTED_GATE_TYPES = {"rectangle", "histogram_range", "polygon"}


def rectangle_gate(
    gate_id: str,
    name: str,
    x_channel: str,
    y_channel: str,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    parent_id: str | None = None,
) -> GateDefinition:
    """Create a rectangle gate definition."""
    return GateDefinition(
        gate_id=gate_id,
        name=name,
        gate_type="rectangle",
        channels=[x_channel, y_channel],
        parent_id=parent_id,
        bounds={"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max},
    )


def histogram_range_gate(
    gate_id: str,
    name: str,
    channel: str,
    minimum: float,
    maximum: float,
    parent_id: str | None = None,
) -> GateDefinition:
    return GateDefinition(
        gate_id=gate_id,
        name=name,
        gate_type="histogram_range",
        channels=[channel],
        parent_id=parent_id,
        bounds={"min": minimum, "max": maximum},
    )


def suggest_candidate_gates(events: pd.DataFrame, channels: list[ChannelSummary], id_prefix: str = "candidate") -> list[GateDefinition]:
    """Suggest conservative review-needed gates from channel metadata and distributions.

    Candidate gates are disabled by default. They are workflow hints for human
    review, not biological truth and not final statistics until accepted.
    """
    suggestions: list[GateDefinition] = []
    fsc, ssc = best_scatter_pair(channels)
    if fsc and ssc and fsc in events and ssc in events:
        gate = _quantile_rectangle(
            f"{id_prefix}_scatter_main",
            "candidate main FSC/SSC population",
            events,
            fsc,
            ssc,
            0.05,
            0.95,
        )
        if gate:
            gate.metadata["candidate_reason"] = "robust central FSC/SSC event cloud; review before use"
            suggestions.append(gate)

    singlet_pair = _singlet_pair(channels)
    if singlet_pair and singlet_pair[0] in events and singlet_pair[1] in events:
        gate = _quantile_rectangle(
            f"{id_prefix}_singlet_review",
            "candidate pulse-geometry singlet review",
            events,
            singlet_pair[0],
            singlet_pair[1],
            0.08,
            0.92,
        )
        if gate:
            gate.metadata["candidate_reason"] = "central pulse-geometry region; review as a singlet-style aid only"
            suggestions.append(gate)
    return suggestions


def apply_gate(events: pd.DataFrame, gate: GateDefinition, parent_mask: np.ndarray | None = None) -> np.ndarray:
    """Compute a boolean membership mask for one gate."""
    if not gate.enabled:
        return np.zeros(len(events), dtype=bool)
    mask = np.ones(len(events), dtype=bool) if parent_mask is None else parent_mask.copy()
    missing = [channel for channel in gate.channels if channel not in events.columns]
    if missing:
        return np.zeros(len(events), dtype=bool)
    if gate.gate_type == "rectangle":
        x, y = gate.channels[:2]
        bounds = gate.bounds
        current = (
            (events[x].to_numpy(dtype=float) >= float(bounds["x_min"]))
            & (events[x].to_numpy(dtype=float) <= float(bounds["x_max"]))
            & (events[y].to_numpy(dtype=float) >= float(bounds["y_min"]))
            & (events[y].to_numpy(dtype=float) <= float(bounds["y_max"]))
        )
    elif gate.gate_type == "histogram_range":
        channel = gate.channels[0]
        bounds = gate.bounds
        current = (
            (events[channel].to_numpy(dtype=float) >= float(bounds["min"]))
            & (events[channel].to_numpy(dtype=float) <= float(bounds["max"]))
        )
    elif gate.gate_type == "polygon":
        x, y = gate.channels[:2]
        current = points_in_polygon(
            events[x].to_numpy(dtype=float),
            events[y].to_numpy(dtype=float),
            gate.vertices,
        )
    else:
        gate.metadata["mask_warning"] = f"unsupported gate type: {gate.gate_type}"
        return np.zeros(len(events), dtype=bool)
    return mask & current


def points_in_polygon(x: np.ndarray, y: np.ndarray, vertices: list[tuple[float, float]]) -> np.ndarray:
    """Vectorized ray-casting point-in-polygon test."""
    if len(vertices) < 3:
        return np.zeros(len(x), dtype=bool)
    inside = np.zeros(len(x), dtype=bool)
    x_vertices = np.array([point[0] for point in vertices], dtype=float)
    y_vertices = np.array([point[1] for point in vertices], dtype=float)
    j = len(vertices) - 1
    for i in range(len(vertices)):
        crosses = ((y_vertices[i] > y) != (y_vertices[j] > y)) & (
            x
            < (x_vertices[j] - x_vertices[i])
            * (y - y_vertices[i])
            / ((y_vertices[j] - y_vertices[i]) or 1e-12)
            + x_vertices[i]
        )
        inside ^= crosses
        j = i
    return inside


def apply_gate_tree(events: pd.DataFrame, gates: list[GateDefinition]) -> dict[str, np.ndarray]:
    """Apply gates with parent-child relationships independent of list order.

    Missing parents, cyclic parents, malformed gates, and unsupported gate
    types become empty masks with a warning in ``gate.metadata``. This keeps
    the UI alive without silently widening a child gate to the root population.
    """
    masks: dict[str, np.ndarray] = {}
    gate_map = {gate.gate_id: gate for gate in gates}
    state: dict[str, str] = {}
    empty = np.zeros(len(events), dtype=bool)

    def resolve(gate: GateDefinition, stack: list[str]) -> np.ndarray:
        if gate.gate_id in masks:
            return masks[gate.gate_id]
        if state.get(gate.gate_id) == "visiting":
            cycle = stack[stack.index(gate.gate_id) :] if gate.gate_id in stack else [gate.gate_id]
            for gate_id in cycle:
                cyclic_gate = gate_map[gate_id]
                cyclic_gate.metadata["mask_warning"] = "cyclic parent relationship"
                masks[gate_id] = empty.copy()
                state[gate_id] = "done"
            return masks[gate.gate_id]

        state[gate.gate_id] = "visiting"
        parent_mask = None
        if gate.parent_id:
            parent = gate_map.get(gate.parent_id)
            if parent is None:
                gate.metadata["mask_warning"] = f"missing parent gate: {gate.parent_id}"
                masks[gate.gate_id] = empty.copy()
                state[gate.gate_id] = "done"
                return masks[gate.gate_id]
            parent_mask = resolve(parent, [*stack, gate.gate_id])
        try:
            masks[gate.gate_id] = apply_gate(events, gate, parent_mask=parent_mask)
        except Exception as exc:
            gate.metadata["mask_warning"] = f"gate could not be applied: {exc}"
            masks[gate.gate_id] = empty.copy()
        state[gate.gate_id] = "done"
        return masks[gate.gate_id]

    for gate in gates:
        resolve(gate, [])
    return masks


def save_gates(gates: list[GateDefinition], path: str | Path) -> Path:
    """Save gate definitions as JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([gate.to_dict() for gate in gates], indent=2), encoding="utf-8")
    return target


def load_gates(path: str | Path) -> list[GateDefinition]:
    """Load gate definitions from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("gate file must contain a JSON list")
    return [GateDefinition.from_dict(item) for item in payload]


def rename_gate(gates: list[GateDefinition], gate_id: str | None, new_name: str | None) -> GateDefinition | None:
    """Rename a gate in place when the id and name are valid."""
    if not gate_id or not new_name or not new_name.strip():
        return None
    gate = find_gate(gates, gate_id)
    if gate is None:
        return None
    gate.name = new_name.strip()
    return gate


def toggle_gate_enabled(gates: list[GateDefinition], gate_id: str | None) -> GateDefinition | None:
    """Flip one gate between enabled and disabled."""
    gate = find_gate(gates, gate_id)
    if gate is None:
        return None
    gate.enabled = not gate.enabled
    return gate


def delete_gate(gates: list[GateDefinition], gate_id: str | None) -> tuple[list[GateDefinition], bool]:
    """Return gates with one id removed."""
    if not gate_id:
        return gates, False
    updated = [gate for gate in gates if gate.gate_id != gate_id]
    return updated, len(updated) != len(gates)


def find_gate(gates: list[GateDefinition], gate_id: str | None) -> GateDefinition | None:
    if not gate_id:
        return None
    return next((gate for gate in gates if gate.gate_id == gate_id), None)


def gate_to_table(gates: list[GateDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "gate_id": gate.gate_id,
            "name": gate.name,
            "type": gate.gate_type,
            "parent": gate.parent_id or "total",
            "channels": ", ".join(gate.channels),
            "status": "candidate - review needed" if gate.candidate else "user-defined",
            "enabled": "yes" if gate.enabled else "no",
            "notes": gate.metadata.get("candidate_reason") or gate.metadata.get("mask_warning", ""),
        }
        for gate in gates
    ]


def _quantile_rectangle(
    gate_id: str,
    name: str,
    events: pd.DataFrame,
    x_channel: str,
    y_channel: str,
    low: float,
    high: float,
) -> GateDefinition | None:
    frame = events[[x_channel, y_channel]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 100:
        return None
    x_min, x_max = frame[x_channel].quantile([low, high])
    y_min, y_max = frame[y_channel].quantile([low, high])
    if not all(np.isfinite(value) for value in [x_min, x_max, y_min, y_max]) or x_min >= x_max or y_min >= y_max:
        return None
    gate = rectangle_gate(gate_id, name, x_channel, y_channel, float(x_min), float(x_max), float(y_min), float(y_max))
    gate.candidate = True
    gate.user_defined = False
    gate.enabled = False
    gate.review_status = "review_needed"
    gate.metadata["candidate"] = "review needed; disabled until accepted"
    return gate


def _singlet_pair(channels: list[ChannelSummary]) -> tuple[str, str] | None:
    role_to_name = {channel.role: channel.raw_name for channel in channels}
    for prefix in ("fsc", "ssc"):
        area = role_to_name.get(f"{prefix}-a")
        for geometry in (f"{prefix}-h", f"{prefix}-w"):
            if area and role_to_name.get(geometry):
                return area, role_to_name[geometry]
    return None
