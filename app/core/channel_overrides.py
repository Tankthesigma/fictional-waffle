from __future__ import annotations

from app.models.sample import SampleRecord


SUPPORTED_ROLE_OVERRIDES = [
    "fsc",
    "fsc-a",
    "fsc-h",
    "fsc-w",
    "ssc",
    "ssc-a",
    "ssc-h",
    "ssc-w",
    "time",
    "fluorescence",
    "index",
    "unknown",
]


def update_channel_role(sample: SampleRecord | None, raw_name: str | None, role: str | None) -> str:
    """Apply a user-reviewed channel role override to a sample."""
    if sample is None:
        raise ValueError("select a sample before overriding channel roles")
    if not raw_name:
        raise ValueError("choose a channel to override")
    normalized = (role or "").strip().lower().replace("_", "-")
    if normalized not in SUPPORTED_ROLE_OVERRIDES:
        raise ValueError(f"unsupported channel role: {role}")
    for channel in sample.channels:
        if channel.raw_name == raw_name:
            old_role = channel.role
            channel.role = normalized
            channel.metadata["user_role_override"] = normalized
            return f"{raw_name}: {old_role} -> {normalized}"
    raise ValueError(f"channel not found: {raw_name}")
