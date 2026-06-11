from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app import __version__
from app.models.gate import GateDefinition
from app.models.qc_flag import QCFlag
from app.models.sample import SampleRecord

DISCLAIMER = "This report is a post-acquisition analysis aid. It does not control any cytometer and does not replace expert review."


def export_pdf_report(
    samples: list[SampleRecord],
    qc_flags: list[QCFlag],
    gates: list[GateDefinition],
    gate_stats: list[dict[str, object]],
    output_path: str | Path,
    title: str = "Ask Flow Workbench Report",
) -> Path:
    """Export a concise PDF report using ReportLab when available."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
    except Exception:
        target.write_text(_plain_report(samples, qc_flags, gates, gate_stats, title), encoding="utf-8")
        return target

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(target), pagesize=letter)
    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated: {datetime.now().isoformat(timespec='seconds')}", styles["Normal"]),
        Paragraph(f"App version: {__version__}", styles["Normal"]),
        Paragraph(DISCLAIMER, styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Uploaded Files", styles["Heading2"]),
    ]
    sample_rows = [["Sample ID", "Filename", "Events", "Channels", "Condition"]]
    sample_rows.extend([[s.sample_id, s.filename, s.event_count, s.channel_count, s.condition or ""] for s in samples])
    story.append(Table(sample_rows))
    story.extend([Spacer(1, 12), Paragraph("QC Summary", styles["Heading2"])])
    qc_rows = [["Sample", "Severity", "Code", "Title"]]
    qc_rows.extend([[f.sample_id, f.severity, f.code, f.title] for f in qc_flags] or [["", "", "", "No QC flags"]])
    story.append(Table(qc_rows))
    story.extend([Spacer(1, 12), Paragraph("Gate Tree", styles["Heading2"])])
    gate_rows = [["Gate", "Type", "Parent", "Channels"]]
    gate_rows.extend([[g.name, g.gate_type, g.parent_id or "total", ", ".join(g.channels)] for g in gates] or [["No gates", "", "", ""]])
    story.append(Table(gate_rows))
    story.extend([Spacer(1, 12), Paragraph("Gate Statistics", styles["Heading2"])])
    if gate_stats:
        keys = list(gate_stats[0].keys())[:8]
        story.append(Table([keys] + [[row.get(key, "") for key in keys] for row in gate_stats[:20]]))
    else:
        story.append(Paragraph("No gate statistics available.", styles["Normal"]))
    doc.build(story)
    return target


def _plain_report(samples: list[SampleRecord], qc_flags: list[QCFlag], gates: list[GateDefinition], gate_stats: list[dict[str, object]], title: str) -> str:
    lines = [title, f"Generated: {datetime.now().isoformat(timespec='seconds')}", f"App version: {__version__}", DISCLAIMER, ""]
    lines.append("Samples:")
    lines.extend(f"- {s.sample_id}: {s.filename}, {s.event_count} events, {s.channel_count} channels" for s in samples)
    lines.append("\nQC:")
    lines.extend(f"- {f.sample_id} {f.severity} {f.code}: {f.title}" for f in qc_flags)
    lines.append("\nGates:")
    lines.extend(f"- {g.name}: {g.gate_type} on {', '.join(g.channels)}" for g in gates)
    lines.append(f"\nGate stat rows: {len(gate_stats)}")
    return "\n".join(lines)
