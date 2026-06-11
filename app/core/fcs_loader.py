from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.compensation import apply_spillover_compensation, parse_spillover
from app.models.sample import SampleRecord


@dataclass(slots=True)
class LoadResult:
    sample: SampleRecord | None
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return self.sample is not None and not self.errors


def load_fcs_file(path: str | Path, sample_id: str | None = None) -> LoadResult:
    """Load an FCS file with FlowIO and return a SampleRecord.

    Bad files return a structured error instead of raising into the UI.
    """
    target = Path(path)
    if target.suffix.lower() != ".fcs":
        return LoadResult(None, [f"{target.name} is not an .fcs file"], [])
    if not target.exists():
        return LoadResult(None, [f"{target} does not exist"], [])
    try:
        from flowio import FlowData  # type: ignore
    except Exception:
        return LoadResult(
            None,
            ["FlowIO is not installed. Install requirements.txt to parse FCS files."],
            [],
        )

    try:
        flow_data, load_warnings = _read_flow_data(FlowData, target)
        keywords = _extract_keywords(flow_data)
        channel_names = _extract_channel_names(flow_data, keywords)
        event_count = _extract_event_count(flow_data, keywords)
        events = _events_to_dataframe(flow_data, event_count, channel_names)
        record = SampleRecord(
            sample_id=sample_id or _safe_sample_id(target),
            filename=target.name,
            path=target,
            file_type="fcs",
            events=events,
            keywords=keywords,
            fcs_version=_extract_fcs_version(flow_data, keywords),
        )
        record.channels = summarize_channels(record.events, record.keywords)
        record.spillover = parse_spillover(record.keywords)
        record.compensated_events, record.compensation_warnings = apply_spillover_compensation(record.events, record.spillover)
        return LoadResult(record, [], load_warnings)
    except Exception as exc:
        return LoadResult(None, [f"Could not parse {target.name}: {exc}"], [])


def file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_flow_data(flow_data_class: Any, target: Path) -> tuple[Any, list[str]]:
    """Read an FCS file, retrying known benign offset issues with a warning."""
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            flow_data = flow_data_class(str(target))
        return flow_data, [f"{target.name}: {item.message}" for item in captured]
    except Exception as exc:
        message = str(exc)
        if "ignore_offset_error" not in message and "data offset" not in message.lower():
            raise
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                flow_data = flow_data_class(str(target), ignore_offset_error=True)
        except TypeError:
            raise exc
        warning_messages = [f"{target.name}: {item.message}" for item in captured]
        warning_messages.append(f"{target.name}: FlowIO reported a data offset mismatch; loaded with ignore_offset_error=True for review.")
        return flow_data, warning_messages


def _events_to_dataframe(flow_data: Any, event_count: int, channel_names: list[str]) -> pd.DataFrame:
    events = getattr(flow_data, "events", None)
    if events is None:
        events = getattr(flow_data, "event_data", None)
    arr = np.asarray(events, dtype=float)
    if arr.ndim == 1:
        if event_count <= 0:
            event_count = int(len(arr) / max(len(channel_names), 1))
        arr = arr.reshape((event_count, len(channel_names)))
    if arr.shape[1] != len(channel_names):
        channel_names = [f"Channel {idx + 1}" for idx in range(arr.shape[1])]
    return pd.DataFrame(arr, columns=channel_names)


def _extract_keywords(flow_data: Any) -> dict[str, Any]:
    keywords: dict[str, Any] = {}
    for attr in ("text", "text_segment", "keywords"):
        value = getattr(flow_data, attr, None)
        if isinstance(value, dict):
            keywords.update({str(k): v for k, v in value.items()})
    return keywords


def _extract_channel_names(flow_data: Any, keywords: dict[str, Any]) -> list[str]:
    channels = getattr(flow_data, "channels", None)
    names: list[str] = []
    if isinstance(channels, dict):
        for index in sorted(channels, key=_channel_sort_key):
            info = channels[index]
            if isinstance(info, dict):
                names.append(str(info.get("PnN") or info.get("pnn") or info.get("name") or f"Channel {index}"))
    if names:
        return names
    par = _keyword_int(keywords, "$PAR") or _keyword_int(keywords, "par") or 0
    for idx in range(1, par + 1):
        name = _keyword_lookup(keywords, f"$P{idx}N", f"p{idx}n", f"P{idx}N") or f"Channel {idx}"
        names.append(str(name))
    return names


def _channel_sort_key(item: object) -> tuple[int, int | str]:
    text = str(item)
    if text.isdigit():
        return (0, int(text))
    return (1, text)


def _extract_event_count(flow_data: Any, keywords: dict[str, Any]) -> int:
    for attr in ("event_count", "event_count_total"):
        value = getattr(flow_data, attr, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
    return _keyword_int(keywords, "$TOT") or _keyword_int(keywords, "tot") or 0


def _extract_fcs_version(flow_data: Any, keywords: dict[str, Any]) -> str | None:
    for attr in ("fcs_version", "version"):
        value = getattr(flow_data, attr, None)
        if value:
            return str(value)
    version = _keyword_lookup(keywords, "$FCSVERSION", "fcs_version")
    return str(version) if version else None


def _keyword_lookup(keywords: dict[str, Any], *keys: str) -> Any:
    lowered = {str(k).lower(): v for k, v in keywords.items()}
    for key in keys:
        if key in keywords:
            return keywords[key]
        if key.lower() in lowered:
            return lowered[key.lower()]
    return None


def _keyword_int(keywords: dict[str, Any], key: str) -> int | None:
    value = _keyword_lookup(keywords, key)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_sample_id(path: Path) -> str:
    stem = path.stem.strip() or "sample"
    safe = "".join(ch if ch.isalnum() else "_" for ch in stem).strip("_").lower()
    return safe or "sample"
