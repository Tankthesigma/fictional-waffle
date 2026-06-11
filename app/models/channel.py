from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChannelSummary:
    """Computed metadata and distribution summary for one channel."""

    index: int
    raw_name: str
    display_label: str | None = None
    marker: str | None = None
    antibody: str | None = None
    fluorochrome: str | None = None
    role: str = "unknown"
    minimum: float | None = None
    maximum: float | None = None
    p1: float | None = None
    p5: float | None = None
    median: float | None = None
    p95: float | None = None
    p99: float | None = None
    range_value: float | None = None
    percent_near_min: float = 0.0
    percent_near_max: float = 0.0
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        panel_parts = [part for part in [self.marker, self.fluorochrome] if part]
        if panel_parts:
            return f"{' '.join(panel_parts)} ({self.raw_name})"
        return self.display_label or self.raw_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "raw_name": self.raw_name,
            "display_label": self.display_label,
            "marker": self.marker,
            "antibody": self.antibody,
            "fluorochrome": self.fluorochrome,
            "role": self.role,
            "min": self.minimum,
            "max": self.maximum,
            "p1": self.p1,
            "p5": self.p5,
            "median": self.median,
            "p95": self.p95,
            "p99": self.p99,
            "range": self.range_value,
            "percent_near_min": self.percent_near_min,
            "percent_near_max": self.percent_near_max,
            "notes": "; ".join(self.notes),
        }
