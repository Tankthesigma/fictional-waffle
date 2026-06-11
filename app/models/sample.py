from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from app.models.channel import ChannelSummary
from app.core.compensation import SpilloverInfo


@dataclass(slots=True)
class SampleRecord:
    """One uploaded event-level sample and its derived metadata."""

    sample_id: str
    filename: str
    path: Path
    file_type: str
    events: pd.DataFrame
    keywords: dict[str, Any] = field(default_factory=dict)
    fcs_version: str | None = None
    channels: list[ChannelSummary] = field(default_factory=list)
    spillover: SpilloverInfo | None = None
    compensated_events: pd.DataFrame | None = None
    compensation_warnings: list[str] = field(default_factory=list)
    condition: str | None = None
    replicate: str | None = None
    control_type: str | None = None
    notes: str | None = None
    limitations: list[str] = field(default_factory=list)

    @property
    def event_count(self) -> int:
        return int(len(self.events))

    @property
    def channel_count(self) -> int:
        return int(len(self.events.columns))

    @property
    def fluorescence_channels(self) -> list[str]:
        return [c.raw_name for c in self.channels if c.role == "fluorescence"]

    @property
    def has_compensated_view(self) -> bool:
        return self.compensated_events is not None

    def channel_by_role(self, role_prefix: str) -> ChannelSummary | None:
        for channel in self.channels:
            if channel.role == role_prefix or channel.role.startswith(f"{role_prefix}-"):
                return channel
        return None

    def to_summary_dict(self, qc_summary: str = "not reviewed") -> dict[str, Any]:
        fsc = self.channel_by_role("fsc")
        ssc = self.channel_by_role("ssc")
        time = self.channel_by_role("time")
        return {
            "sample_id": self.sample_id,
            "filename": self.filename,
            "event_count": self.event_count,
            "fcs_version": self.fcs_version or "",
            "channel_count": self.channel_count,
            "primary_fsc": fsc.raw_name if fsc else "",
            "primary_ssc": ssc.raw_name if ssc else "",
            "time_channel": time.raw_name if time else "",
            "fluorescence_channels": len(self.fluorescence_channels),
            "qc_status": qc_summary,
            "condition": self.condition or "",
            "replicate": self.replicate or "",
        }
