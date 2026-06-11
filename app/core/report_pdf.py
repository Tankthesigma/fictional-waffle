from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app import __version__
from app.core.disclaimers import REPORT_DISCLAIMER
from app.core.report_outline import report_outline
from app.models.gate import GateDefinition
from app.models.qc_flag import QCFlag
from app.models.sample import SampleRecord

DISCLAIMER = REPORT_DISCLAIMER


def export_pdf_report(
    samples: list[SampleRecord],
    qc_flags: list[QCFlag],
    gates: list[GateDefinition],
    gate_stats: list[dict[str, object]],
    output_path: str | Path,
    title: str = "Ask Flow Workbench Report",
    figure_paths: list[str | Path] | None = None,
    comparison_rows: list[dict[str, object]] | None = None,
) -> Path:
    """Export a concise PDF report using ReportLab when available."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table
    except Exception:
        target.write_text(_plain_report(samples, qc_flags, gates, gate_stats, title, comparison_rows or []), encoding="utf-8")
        return target

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(target), pagesize=letter)
    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated: {datetime.now().isoformat(timespec='seconds')}", styles["Normal"]),
        Paragraph(f"App version: {__version__}", styles["Normal"]),
        Paragraph(DISCLAIMER, styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Analysis Review Notes", styles["Heading2"]),
    ]
    outline_rows = [["Section", "Status", "Note", "Detail"]]
    outline_rows.extend([[row["section"], row["status"], row["note"], row["detail"]] for row in report_outline(samples, qc_flags, gates, gate_stats, comparison_rows or [])])
    story.extend(
        [
            Table(outline_rows),
            Spacer(1, 12),
        ]
    )
    story.extend([
        Paragraph("Uploaded Files", styles["Heading2"]),
    ])
    sample_rows = [["Sample ID", "Filename", "Events", "Channels", "Condition"]]
    sample_rows.extend([[s.sample_id, s.filename, s.event_count, s.channel_count, s.condition or ""] for s in samples])
    story.append(Table(sample_rows))
    channel_rows = _channel_summary_rows(samples)
    if channel_rows:
        story.extend([Spacer(1, 12), Paragraph("Channel And Panel Summary", styles["Heading2"])])
        story.append(Table([["Sample", "Channel", "Label", "Role", "Marker", "Fluorochrome"]] + channel_rows[:30]))
    figures = _existing_figures(figure_paths)
    if figures:
        story.extend([Spacer(1, 12), Paragraph("Representative Plots", styles["Heading2"])])
        for figure_path in figures:
            story.append(Image(str(figure_path), width=480, height=300))
            story.append(Spacer(1, 8))
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
    if comparison_rows:
        story.extend([Spacer(1, 12), Paragraph("Exploratory Comparison", styles["Heading2"])])
        comparison_keys = ["channel", "control_median", "treated_median", "median_difference", "fold_change", "n_control", "n_treated", "notes"]
        story.append(Table([comparison_keys] + [[row.get(key, "") for key in comparison_keys] for row in comparison_rows[:20]]))
    doc.build(story)
    return target


def _plain_report(
    samples: list[SampleRecord],
    qc_flags: list[QCFlag],
    gates: list[GateDefinition],
    gate_stats: list[dict[str, object]],
    title: str,
    comparison_rows: list[dict[str, object]],
) -> str:
    lines = [title, f"Generated: {datetime.now().isoformat(timespec='seconds')}", f"App version: {__version__}", DISCLAIMER, ""]
    lines.append("Analysis Review Notes:")
    lines.extend(
        f"- {row['section']} [{row['status']}]: {row['note']} {row['detail']}"
        for row in report_outline(samples, qc_flags, gates, gate_stats, comparison_rows)
    )
    lines.append("")
    lines.append("Samples:")
    lines.extend(f"- {s.sample_id}: {s.filename}, {s.event_count} events, {s.channel_count} channels" for s in samples)
    lines.append("\nChannels:")
    for sample, channel, label, role, marker, fluorochrome in _channel_summary_rows(samples)[:30]:
        lines.append(f"- {sample} {channel}: {label}, {role}, {marker}, {fluorochrome}")
    lines.append("\nQC:")
    lines.extend(f"- {f.sample_id} {f.severity} {f.code}: {f.title}" for f in qc_flags)
    lines.append("\nGates:")
    lines.extend(f"- {g.name}: {g.gate_type} on {', '.join(g.channels)}" for g in gates)
    lines.append(f"\nGate stat rows: {len(gate_stats)}")
    lines.append("\nExploratory Comparison:")
    lines.extend(
        f"- {row.get('channel')}: difference={row.get('median_difference')}, fold_change={row.get('fold_change')}, notes={row.get('notes')}"
        for row in comparison_rows
    )
    return "\n".join(lines)


def _existing_figures(figure_paths: list[str | Path] | None) -> list[Path]:
    return [Path(path) for path in figure_paths or [] if Path(path).exists()]


def _channel_summary_rows(samples: list[SampleRecord]) -> list[list[object]]:
    rows: list[list[object]] = []
    for sample in samples:
        for channel in sample.channels:
            rows.append(
                [
                    sample.sample_id,
                    channel.raw_name,
                    channel.label,
                    channel.role,
                    channel.marker or "",
                    channel.fluorochrome or "",
                ]
            )
    return rows
