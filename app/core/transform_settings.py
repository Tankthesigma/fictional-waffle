from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_TRANSFORMS = {"raw", "safe_log10", "arcsinh", "logicle"}


@dataclass(frozen=True, slots=True)
class ChannelTransform:
    """Display transform resolved for one channel."""

    transform: str
    cofactor: float
    source: str = "global"


def normalize_channel_overrides(payload: Any) -> dict[str, dict[str, object]]:
    """Return a safe channel override mapping from Dash/project payloads."""
    if not isinstance(payload, dict):
        return {}
    raw_overrides = payload.get("channel_overrides", payload)
    if not isinstance(raw_overrides, dict):
        return {}
    normalized: dict[str, dict[str, object]] = {}
    for channel, settings in raw_overrides.items():
        if not channel or not isinstance(settings, dict):
            continue
        transform = str(settings.get("transform") or "").strip()
        if transform not in SUPPORTED_TRANSFORMS:
            continue
        try:
            cofactor = float(settings.get("cofactor", 150) or 150)
        except (TypeError, ValueError):
            cofactor = 150.0
        normalized[str(channel)] = {"transform": transform, "cofactor": max(cofactor, 1.0)}
    return normalized


def resolve_channel_transform(
    channel: str | None,
    global_transform: str | None,
    global_cofactor: object,
    overrides: Any,
) -> ChannelTransform:
    """Resolve the display transform for one channel."""
    transform = str(global_transform or "raw")
    try:
        cofactor = float(global_cofactor or 150)
    except (TypeError, ValueError):
        cofactor = 150.0
    source = "global"
    normalized = normalize_channel_overrides(overrides)
    if channel and channel in normalized:
        settings = normalized[channel]
        transform = str(settings["transform"])
        cofactor = float(settings["cofactor"])
        source = "channel"
    return ChannelTransform(transform=transform, cofactor=max(cofactor, 1.0), source=source)


def override_rows(overrides: Any) -> list[dict[str, object]]:
    """Rows for the transform override UI table."""
    return [
        {"channel": channel, "transform": settings["transform"], "cofactor": settings["cofactor"]}
        for channel, settings in sorted(normalize_channel_overrides(overrides).items())
    ]
