from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


GateType = Literal["rectangle", "polygon", "histogram_range"]


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
        return cls(
            gate_id=str(payload["gate_id"]),
            name=str(payload.get("name") or payload["gate_id"]),
            gate_type=payload.get("gate_type", "rectangle"),
            channels=list(payload.get("channels", [])),
            parent_id=payload.get("parent_id"),
            enabled=bool(payload.get("enabled", True)),
            user_defined=bool(payload.get("user_defined", True)),
            candidate=bool(payload.get("candidate", False)),
            review_status=str(payload.get("review_status", "accepted")),
            vertices=[tuple(v) for v in payload.get("vertices", [])],
            bounds=dict(payload.get("bounds", {})),
            metadata=dict(payload.get("metadata", {})),
        )
