from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.fcs_export import export_events_fcs
from app.models.sample import SampleRecord


@dataclass(frozen=True, slots=True)
class ConcatenationResult:
    """Result of concatenating compatible samples."""

    sample: SampleRecord | None
    skipped: list[str]
    mapping_rows: list[dict[str, object]]


def concatenate_samples(samples: list[SampleRecord], sample_ids: list[str] | None = None, *, sample_id: str = "concatenated_batch") -> ConcatenationResult:
    """Concatenate compatible samples and add an AFW_SAMPLE_INDEX provenance channel."""
    selected = [sample for sample in samples if not sample_ids or sample.sample_id in sample_ids]
    if not selected:
        return ConcatenationResult(None, ["No samples were selected for concatenation."], [])
    reference_channels = list(selected[0].events.columns)
    frames: list[pd.DataFrame] = []
    mapping: list[dict[str, object]] = []
    skipped: list[str] = []
    for sample_index, sample in enumerate(selected, start=1):
        channels = list(sample.events.columns)
        if channels != reference_channels:
            skipped.append(f"{sample.sample_id}: channel order/name mismatch")
            continue
        frame = sample.events.apply(pd.to_numeric, errors="coerce")
        if frame.empty:
            skipped.append(f"{sample.sample_id}: no event rows")
            continue
        frame = frame.copy()
        frame["AFW_SAMPLE_INDEX"] = sample_index
        frames.append(frame)
        mapping.append(
            {
                "sample_index": sample_index,
                "sample_id": sample.sample_id,
                "filename": sample.filename,
                "event_count": sample.event_count,
            }
        )
    if not frames:
        return ConcatenationResult(None, skipped or ["No compatible samples could be concatenated."], mapping)
    events = pd.concat(frames, ignore_index=True)
    derived = SampleRecord(
        sample_id=sample_id,
        filename=f"{sample_id}.derived.csv",
        path=Path(f"derived://{sample_id}"),
        file_type="derived",
        events=events,
        keywords={
            "AFW_DERIVED": "concatenated_samples",
            "AFW_GENERATED_AT": datetime.now().isoformat(timespec="seconds"),
            "AFW_SOURCE_SAMPLE_COUNT": len(mapping),
        },
        condition="concatenated",
        notes="Derived by Ask Flow Workbench from compatible loaded samples.",
        limitations=["Derived local concatenation; AFW_SAMPLE_INDEX maps events to source samples."],
    )
    derived.channels = summarize_channels(derived.events, derived.keywords)
    return ConcatenationResult(derived, skipped, mapping)


def export_concatenated_fcs(sample: SampleRecord, mapping_rows: list[dict[str, object]], output_dir: str | Path) -> tuple[Path, Path]:
    """Export a concatenated sample and its sample-index mapping sidecar."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    fcs_path = target_dir / f"{sample.sample_id}.fcs"
    mapping_path = target_dir / f"{sample.sample_id}_sample-index-map.csv"
    pd.DataFrame(mapping_rows).to_csv(mapping_path, index=False)
    export_events_fcs(
        sample.events,
        fcs_path,
        sample=sample,
        metadata={
            "AFW_EXPORT_TYPE": "concatenated_samples",
            "AFW_SAMPLE_ID": sample.sample_id,
            "AFW_SAMPLE_INDEX_MAP": mapping_path.name,
        },
    )
    return fcs_path, mapping_path
