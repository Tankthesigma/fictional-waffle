from __future__ import annotations

from app.core.compare import comparison_insights
from app.core.disclaimers import REPORT_DISCLAIMER
from app.core.qc import qc_summary
from app.models.gate import GateDefinition
from app.models.qc_flag import QCFlag
from app.models.sample import SampleRecord


def report_outline(
    samples: list[SampleRecord],
    qc_flags: list[QCFlag],
    gates: list[GateDefinition],
    gate_stats: list[dict[str, object]] | None = None,
    comparison_rows: list[dict[str, object]] | None = None,
) -> list[dict[str, str]]:
    """Build deterministic review notes for report preview and exports."""
    gate_stats = gate_stats or []
    comparison_rows = comparison_rows or []
    enabled_gates = [gate for gate in gates if gate.enabled and not gate.candidate]
    candidate_gates = [gate for gate in gates if gate.candidate]
    comparison_note = comparison_insights(comparison_rows)[1] if comparison_rows else None
    gate_stats_note = f"{len(gate_stats)} statistics row(s)" if gate_stats else ("statistics computed during export" if gates else "no gate statistics")
    return [
        {
            "section": "Scope",
            "status": "ready" if samples else "waiting",
            "note": f"{len(samples)} sample(s), {sum(sample.event_count for sample in samples):,} event(s), {sum(sample.channel_count for sample in samples)} channel row(s).",
            "detail": "FCS metadata and optional panel CSV labels are summarized without embedding raw event matrices.",
        },
        {
            "section": "QC",
            "status": "review" if qc_flags else ("ready" if samples else "waiting"),
            "note": qc_summary(qc_flags),
            "detail": f"{len(qc_flags)} rule-based QC flag(s); warnings are review prompts, not pass/fail conclusions.",
        },
        {
            "section": "Gates",
            "status": "review" if candidate_gates else ("ready" if enabled_gates else "waiting"),
            "note": f"{len(enabled_gates)} enabled gate(s), {len(candidate_gates)} candidate gate(s), {gate_stats_note}.",
            "detail": "Candidate and quick-review gates require human review before final interpretation.",
        },
        {
            "section": "Comparison",
            "status": "review" if comparison_rows else "waiting",
            "note": comparison_note["message"] if comparison_note else "No exploratory control-vs-treated comparison rows are selected.",
            "detail": comparison_note["detail"] if comparison_note else "Generate comparisons from grouped samples before exporting comparison notes.",
        },
        {
            "section": "Boundary",
            "status": "ready",
            "note": "Post-acquisition analysis support only.",
            "detail": REPORT_DISCLAIMER,
        },
    ]


def report_outline_bullets(outline: list[dict[str, str]]) -> list[str]:
    """Flatten report outline cards into export-friendly bullet strings."""
    return [f"{row['section']}: {row['note']} {row['detail']}" for row in outline]
