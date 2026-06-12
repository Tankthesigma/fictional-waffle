from __future__ import annotations

from dataclasses import dataclass

from app.core.channel_inference import best_scatter_pair
from app.models.channel import ChannelSummary
from app.models.sample import SampleRecord


@dataclass(frozen=True, slots=True)
class PlotPreset:
    """A role-inferred plot setup that reduces manual channel picking."""

    preset_id: str
    label: str
    x_channel: str | None
    y_channel: str | None
    hist_channel: str | None
    plot_mode: str
    transform: str
    description: str

    def option(self) -> dict[str, str]:
        return {"label": self.label, "value": self.preset_id}


def recommended_plot_presets(sample: SampleRecord | None) -> list[PlotPreset]:
    """Infer practical plot presets from channel roles and panel labels."""
    if sample is None:
        return []
    presets: list[PlotPreset] = []
    fsc, ssc = best_scatter_pair(sample.channels)
    first_fluor = _first_role(sample.channels, "fluorescence")
    time = _first_role(sample.channels, "time")
    area, height_or_width = _pulse_pair(sample.channels)

    if fsc and ssc:
        presets.append(
            PlotPreset(
                preset_id="scatter-cleanup",
                label="Scatter Cleanup",
                x_channel=fsc,
                y_channel=ssc,
                hist_channel=first_fluor.raw_name if first_fluor else None,
                plot_mode="density",
                transform="arcsinh",
                description="FSC/SSC density view for debris and main-population review.",
            )
        )
    if area and height_or_width:
        presets.append(
            PlotPreset(
                preset_id="singlet-check",
                label="Singlet Check",
                x_channel=area.raw_name,
                y_channel=height_or_width.raw_name,
                hist_channel=first_fluor.raw_name if first_fluor else None,
                plot_mode="scatter",
                transform="raw",
                description="Pulse-geometry scatter view for doublet-review context.",
            )
        )
    if first_fluor:
        presets.append(
            PlotPreset(
                preset_id="marker-histogram",
                label=f"{_short_label(first_fluor)} Histogram",
                x_channel=fsc,
                y_channel=ssc,
                hist_channel=first_fluor.raw_name,
                plot_mode="scatter",
                transform="arcsinh",
                description="Overlay-ready marker histogram with cytometry-friendly display scaling.",
            )
        )
    if time:
        presets.append(
            PlotPreset(
                preset_id="time-review",
                label="Time Review",
                x_channel=time.raw_name,
                y_channel=fsc or ssc,
                hist_channel=first_fluor.raw_name if first_fluor else None,
                plot_mode="scatter",
                transform="raw",
                description="Time-vs-signal view for acquisition stability review.",
            )
        )
    if not presets and len(sample.channels) >= 2:
        presets.append(
            PlotPreset(
                preset_id="first-two-channels",
                label="First Two Channels",
                x_channel=sample.channels[0].raw_name,
                y_channel=sample.channels[1].raw_name,
                hist_channel=sample.channels[0].raw_name,
                plot_mode="scatter",
                transform="raw",
                description="Fallback view because FSC/SSC roles were not confidently identified.",
            )
        )
    return presets


def resolve_plot_preset(sample: SampleRecord | None, preset_id: str | None) -> PlotPreset | None:
    """Return the requested preset, or the first recommendation if none is chosen."""
    presets = recommended_plot_presets(sample)
    if not presets:
        return None
    if preset_id:
        for preset in presets:
            if preset.preset_id == preset_id:
                return preset
    return presets[0]


def plot_preset_rows(sample: SampleRecord | None) -> list[dict[str, str]]:
    """Build UI rows explaining the available preset recommendations."""
    return [
        {
            "preset": preset.label,
            "scatter": _axis_pair(preset.x_channel, preset.y_channel),
            "histogram": preset.hist_channel or "",
            "mode": preset.plot_mode,
            "transform": preset.transform,
            "why": preset.description,
        }
        for preset in recommended_plot_presets(sample)
    ]


def _first_role(channels: list[ChannelSummary], role: str) -> ChannelSummary | None:
    return next((channel for channel in channels if channel.role == role), None)


def _pulse_pair(channels: list[ChannelSummary]) -> tuple[ChannelSummary | None, ChannelSummary | None]:
    for prefix in ("fsc", "ssc"):
        area = _first_role(channels, f"{prefix}-a")
        height = _first_role(channels, f"{prefix}-h")
        width = _first_role(channels, f"{prefix}-w")
        if area and (height or width):
            return area, height or width
    return None, None


def _short_label(channel: ChannelSummary) -> str:
    if channel.marker and channel.fluorochrome:
        return f"{channel.marker} {channel.fluorochrome}"
    if channel.marker:
        return channel.marker
    if channel.fluorochrome:
        return channel.fluorochrome
    return channel.raw_name


def _axis_pair(x_channel: str | None, y_channel: str | None) -> str:
    if not x_channel and not y_channel:
        return ""
    return f"{x_channel or 'select'} x {y_channel or 'select'}"
