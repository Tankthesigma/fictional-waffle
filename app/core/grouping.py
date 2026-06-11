from __future__ import annotations

from collections import Counter

from app.core.csv_loader import MANIFEST_COLUMNS
from app.models.sample import SampleRecord


def grouping_readiness_summary(samples: list[SampleRecord]) -> dict[str, int | str]:
    """Summarize whether samples are ready for grouped comparison."""
    labeled = [sample for sample in samples if _text(sample.condition)]
    groups = Counter(str(sample.condition).strip() for sample in labeled)
    controls = [sample for sample in samples if _is_control(sample)]
    treated = [sample for sample in samples if _is_treated(sample)]
    status = "waiting"
    if samples:
        status = "ready" if len(groups) >= 2 else "needs groups"
    return {
        "sample_count": len(samples),
        "labeled_samples": len(labeled),
        "unlabeled_samples": len(samples) - len(labeled),
        "group_count": len(groups),
        "control_like": len(controls),
        "treated_like": len(treated),
        "status": status,
    }


def grouping_readiness_rows(samples: list[SampleRecord]) -> list[dict[str, str]]:
    """Build per-sample grouping review rows for the Compare tab."""
    rows = []
    for sample in samples:
        status = "ready" if _text(sample.condition) else "needs condition"
        if _text(sample.condition) and not _text(sample.replicate):
            status = "needs replicate"
        rows.append(
            {
                "sample_id": sample.sample_id,
                "file_name": sample.filename,
                "condition": sample.condition or "",
                "replicate": sample.replicate or "",
                "control_type": sample.control_type or "",
                "status": status,
                "next_step": _next_step(status),
            }
        )
    return rows


def manifest_template_rows(samples: list[SampleRecord]) -> list[dict[str, str]]:
    """Generate CSV-ready manifest rows from currently loaded samples."""
    if not samples:
        return [
            {
                "sample_id": "sample_1",
                "file_name": "sample_1.fcs",
                "condition": "control",
                "replicate": "1",
                "control_type": "untreated",
                "notes": "",
            },
            {
                "sample_id": "sample_2",
                "file_name": "sample_2.fcs",
                "condition": "treated",
                "replicate": "1",
                "control_type": "treated",
                "notes": "",
            },
        ]
    return [
        {
            "sample_id": sample.sample_id,
            "file_name": sample.filename,
            "condition": sample.condition or "",
            "replicate": sample.replicate or "",
            "control_type": sample.control_type or "",
            "notes": sample.notes or "",
        }
        for sample in samples
    ]


def manifest_template_columns() -> list[str]:
    return list(MANIFEST_COLUMNS)


def _text(value: object) -> bool:
    return bool(str(value).strip()) if value is not None else False


def _is_control(sample: SampleRecord) -> bool:
    text = f"{sample.condition or ''} {sample.control_type or ''}".lower()
    return any(token in text for token in ("control", "untreated", "vehicle", "unstained", "baseline"))


def _is_treated(sample: SampleRecord) -> bool:
    text = f"{sample.condition or ''} {sample.control_type or ''}".lower()
    return any(token in text for token in ("treated", "stimulated", "drug", "test", "experimental"))


def _next_step(status: str) -> str:
    if status == "needs condition":
        return "Add condition labels with a manifest CSV before comparing groups."
    if status == "needs replicate":
        return "Add replicate labels if exploratory replicate review matters."
    return "Ready for grouping and exploratory comparison."
