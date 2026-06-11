from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ComparisonResult:
    """Exploratory control-versus-treated comparison result."""

    channel: str
    control_median: float | None
    treated_median: float | None
    median_difference: float | None
    fold_change: float | None
    n_control: int
    n_treated: int
    channel_label: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "channel_label": self.channel_label or self.channel,
            "control_median": self.control_median,
            "treated_median": self.treated_median,
            "median_difference": self.median_difference,
            "fold_change": self.fold_change,
            "n_control": self.n_control,
            "n_treated": self.n_treated,
            "notes": "; ".join(self.notes),
        }
