from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.models.gate import GateDefinition


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
        raise ValueError(f"unsupported gate type: {gate.gate_type}")
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
    """Apply gates with parent-child relationships in list order."""
    masks: dict[str, np.ndarray] = {}
    for gate in gates:
        parent_mask = masks.get(gate.parent_id) if gate.parent_id else None
        masks[gate.gate_id] = apply_gate(events, gate, parent_mask=parent_mask)
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
        }
        for gate in gates
    ]
