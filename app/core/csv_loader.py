from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.channel_inference import summarize_channels
from app.core.fcs_loader import LoadResult
from app.models.sample import SampleRecord


MANIFEST_COLUMNS = ["sample_id", "file_name", "condition", "replicate", "control_type", "notes"]


def load_csv_file(path: str | Path, sample_id: str | None = None) -> LoadResult:
    """Load an event-level CSV or a limited summary CSV."""
    target = Path(path)
    if target.suffix.lower() != ".csv":
        return LoadResult(None, [f"{target.name} is not a .csv file"], [])
    try:
        data = pd.read_csv(target)
    except Exception as exc:
        return LoadResult(None, [f"Could not parse {target.name}: {exc}"], [])

    numeric = data.select_dtypes(include="number")
    limitations: list[str] = []
    if numeric.shape[1] < 2 or len(numeric) < 10:
        limitations.append("CSV appears to contain summary data, not event-level cytometry data.")
        events = numeric if not numeric.empty else data.copy()
    else:
        events = numeric.copy()
    record = SampleRecord(
        sample_id=sample_id or _safe_sample_id(target),
        filename=target.name,
        path=target,
        file_type="csv",
        events=events,
        keywords={"source": "csv", "columns": ",".join(data.columns)},
        limitations=limitations,
    )
    record.channels = summarize_channels(record.events, record.keywords)
    return LoadResult(record, [], limitations)


def parse_manifest(path: str | Path) -> dict[str, dict[str, str]]:
    """Parse an optional manifest CSV keyed by file_name."""
    data = pd.read_csv(path).fillna("")
    missing = [column for column in ("sample_id", "file_name") if column not in data.columns]
    if missing:
        raise ValueError(f"manifest missing required columns: {', '.join(missing)}")
    manifest: dict[str, dict[str, str]] = {}
    for _, row in data.iterrows():
        item = {column: str(row[column]) for column in data.columns if column in MANIFEST_COLUMNS}
        manifest[item["file_name"]] = item
    return manifest


def apply_manifest(records: list[SampleRecord], manifest: dict[str, dict[str, str]]) -> None:
    """Apply manifest metadata to loaded samples in place."""
    for record in records:
        item = manifest.get(record.filename)
        if not item:
            continue
        record.sample_id = item.get("sample_id") or record.sample_id
        record.condition = item.get("condition") or None
        record.replicate = item.get("replicate") or None
        record.control_type = item.get("control_type") or None
        record.notes = item.get("notes") or None


def _safe_sample_id(path: Path) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in path.stem).strip("_").lower()
    return safe or "sample"
