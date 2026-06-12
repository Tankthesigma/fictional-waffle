from __future__ import annotations

from app.models.sample import SampleRecord


def channel_label(sample: SampleRecord | None, raw_name: str | None) -> str:
    """Return the best human-facing label for a raw channel name."""
    if not raw_name:
        return "Select channel"
    if sample is None:
        return raw_name
    for channel in sample.channels:
        if channel.raw_name == raw_name:
            return channel.label
    return raw_name


def channel_label_map(samples: list[SampleRecord]) -> dict[str, str]:
    """Build a stable raw-channel to marker-aware label map from samples."""
    labels: dict[str, str] = {}
    for sample in samples:
        for channel in sample.channels:
            label = channel.label
            if channel.raw_name not in labels or label != channel.raw_name:
                labels[channel.raw_name] = label
    return labels
