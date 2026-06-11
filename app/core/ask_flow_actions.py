from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.models.sample import SampleRecord


@dataclass(slots=True)
class AskFlowActionPlan:
    """Safe UI updates requested through Ask Flow."""

    updates: dict[str, Any] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)

    @property
    def has_actions(self) -> bool:
        return bool(self.updates)


def plan_actions(question: str, samples: list[SampleRecord], sample: SampleRecord | None) -> AskFlowActionPlan:
    """Translate plain-English chat into allowlisted workbench UI updates."""
    text = (question or "").strip()
    normalized = text.lower()
    plan = AskFlowActionPlan()
    if not text:
        return plan

    selected = _sample_from_text(normalized, samples) or sample
    if selected is not None and sample is not None and selected.sample_id != sample.sample_id:
        plan.updates["sample_id"] = selected.sample_id
        plan.messages.append(f"Selected sample {selected.sample_id}.")
    elif selected is not None and sample is None:
        plan.updates["sample_id"] = selected.sample_id
        plan.messages.append(f"Selected sample {selected.sample_id}.")

    working_sample = selected or sample
    if working_sample is None:
        return plan

    if any(token in normalized for token in ("density", "heatmap")):
        plan.updates["plot_mode"] = "density"
        plan.messages.append("Switched the scatter view to density mode.")
    elif "contour" in normalized:
        plan.updates["plot_mode"] = "contour"
        plan.messages.append("Switched the scatter view to contour mode.")
    elif any(token in normalized for token in ("dot plot", "scatter", "scatterplot")):
        plan.updates["plot_mode"] = "scatter"
        plan.messages.append("Switched the scatter view to dot plot mode.")

    if "arcsinh" in normalized:
        plan.updates["transform"] = "arcsinh"
        plan.messages.append("Set the display transform to arcsinh.")
    elif "logicle" in normalized:
        plan.updates["transform"] = "logicle"
        plan.messages.append("Set the display transform to logicle when supported.")
    elif "log10" in normalized or "safe log" in normalized:
        plan.updates["transform"] = "safe_log10"
        plan.messages.append("Set the display transform to safe log10.")
    elif re.search(r"\b(raw|linear)\b", normalized):
        plan.updates["transform"] = "raw"
        plan.messages.append("Set the display transform to raw/linear.")

    max_events = _max_events_from_text(normalized)
    if max_events is not None:
        plan.updates["max_events"] = max_events
        plan.messages.append(f"Set max plotted events to {max_events:,}.")

    x_channel, y_channel = _scatter_pair_from_text(text, working_sample)
    if x_channel and y_channel:
        plan.updates["x_channel"] = x_channel
        plan.updates["y_channel"] = y_channel
        plan.messages.append(f"Set scatter axes to {x_channel} vs {y_channel}.")

    histogram_channel = _histogram_channel_from_text(text, working_sample)
    if histogram_channel:
        plan.updates["hist_channel"] = histogram_channel
        plan.messages.append(f"Set histogram channel to {histogram_channel}.")

    return plan


def _sample_from_text(normalized: str, samples: list[SampleRecord]) -> SampleRecord | None:
    for sample in samples:
        candidates = {sample.sample_id.lower(), sample.filename.lower()}
        if any(candidate and candidate in normalized for candidate in candidates):
            return sample
    return None


def _scatter_pair_from_text(text: str, sample: SampleRecord) -> tuple[str | None, str | None]:
    if " vs " not in text.lower() and " versus " not in text.lower():
        return None, None
    parts = re.split(r"\b(?:vs|versus)\b", text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None, None
    left = _channel_from_text(parts[0], sample)
    right = _channel_from_text(parts[1], sample)
    return left, right


def _histogram_channel_from_text(text: str, sample: SampleRecord) -> str | None:
    normalized = text.lower()
    if "hist" not in normalized and "distribution" not in normalized:
        return None
    return _channel_from_text(text, sample)


def _channel_from_text(text: str, sample: SampleRecord) -> str | None:
    normalized = text.lower()
    matches: list[tuple[int, str]] = []
    for channel in sample.channels:
        aliases = {
            channel.raw_name,
            channel.display_label or "",
            channel.marker or "",
            channel.fluorochrome or "",
            channel.label,
        }
        for alias in aliases:
            alias = alias.strip()
            if not alias:
                continue
            index = normalized.find(alias.lower())
            if index >= 0:
                matches.append((index, channel.raw_name))
    if not matches:
        return None
    return sorted(matches, key=lambda item: item[0])[0][1]


def _max_events_from_text(normalized: str) -> int | None:
    match = re.search(r"(?:max|show|display|plot)\D{0,24}([0-9][0-9,]{3,})\s*(?:events|points)?", normalized)
    if not match:
        return None
    value = int(match.group(1).replace(",", ""))
    return max(1_000, min(value, 1_000_000))
