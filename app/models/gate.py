from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


GateType = Literal["rectangle", "polygon", "histogram_range", "ellipse", "quadrant", "bi_range", "boolean"]
SUPPORTED_GATE_TYPES = {"rectangle", "polygon", "histogram_range", "ellipse", "quadrant", "bi_range", "boolean"}


@dataclass(slots=True)
class GateDefinition:
    """Serializable user or candidate gate definition."""

    gate_id: str
    name: str
    gate_type: GateType
    channels: list[str]
    parent_id: str | None = None
    enabled: bool = True
    user_defined: bool = True
    candidate: bool = False
    review_status: str = "accepted"
    vertices: list[tuple[float, float]] = field(default_factory=list)
    bounds: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "gate_type": self.gate_type,
            "channels": self.channels,
            "parent_id": self.parent_id,
            "enabled": self.enabled,
            "user_defined": self.user_defined,
            "candidate": self.candidate,
            "review_status": self.review_status,
            "vertices": [list(v) for v in self.vertices],
            "bounds": self.bounds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GateDefinition":
        if not isinstance(payload, dict):
            raise ValueError("gate definition must be an object")
        gate_type = str(payload.get("gate_type", "rectangle"))
        metadata = dict(payload.get("metadata", {}))
        if gate_type not in SUPPORTED_GATE_TYPES:
            metadata["mask_warning"] = f"unsupported gate type: {gate_type}"
        return cls(
            gate_id=str(payload["gate_id"]),
            name=str(payload.get("name") or payload["gate_id"]),
            gate_type=gate_type,  # type: ignore[arg-type]
            channels=_string_list(payload.get("channels", []), "channels"),
            parent_id=payload.get("parent_id"),
            enabled=bool(payload.get("enabled", True)),
            user_defined=bool(payload.get("user_defined", True)),
            candidate=bool(payload.get("candidate", False)),
            review_status=str(payload.get("review_status", "accepted")),
            vertices=_vertices(payload.get("vertices", [])),
            bounds=dict(payload.get("bounds", {})),
            metadata=metadata,
        )


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [str(item) for item in value]


def _vertices(value: Any) -> list[tuple[float, float]]:
    if not isinstance(value, list):
        raise ValueError("vertices must be a list")
    vertices: list[tuple[float, float]] = []
    for vertex in value:
        if not isinstance(vertex, (list, tuple)) or len(vertex) != 2:
            raise ValueError("polygon vertices must be [x, y] pairs")
        vertices.append((float(vertex[0]), float(vertex[1])))
    return vertices
