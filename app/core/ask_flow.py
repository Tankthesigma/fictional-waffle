from __future__ import annotations

from app.core.compare import comparison_summary
from app.core.qc import qc_summary
from app.core.compensation import compensation_status
from app.models.gate import GateDefinition
from app.models.qc_flag import QCFlag
from app.models.sample import SampleRecord


FORBIDDEN_NOTICE = (
    "Ask Flow summarizes the uploaded data context only. It does not infer cell identity, diagnosis, "
    "instrument settings, or whether a gate is biologically correct."
)


def answer_question(
    question: str,
    sample: SampleRecord | None,
    *,
    x_channel: str | None = None,
    y_channel: str | None = None,
    gates: list[GateDefinition] | None = None,
    qc_flags: list[QCFlag] | None = None,
    comparison_rows: list[dict[str, object]] | None = None,
) -> str:
    """Deterministic local Ask Flow response with no network calls."""
    q = question.lower().strip()
    gates = gates or []
    qc_flags = qc_flags or []
    comparison_rows = comparison_rows or []
    if not sample:
        return "Upload or select a sample first. " + FORBIDDEN_NOTICE
    if "fsc" in q or "ssc" in q or "plot" in q:
        x_label = _channel_label(sample, x_channel)
        y_label = _channel_label(sample, y_channel)
        return (
            f"The current plot uses {x_label} versus {y_label} for sample {sample.sample_id}. "
            f"Those channels are being displayed as {_role_phrase(sample, x_channel)} and {_role_phrase(sample, y_channel)}. "
            f"It is a post-acquisition view for human review; clustering or identity labels require marker context from the user. "
            f"{FORBIDDEN_NOTICE}"
        )
    if "debris" in q:
        debris = [flag for flag in qc_flags if "DEBRIS" in flag.code]
        if debris:
            flag = debris[0]
            return f"{flag.title}: {flag.explanation} Metric={flag.metric_value}, threshold={flag.threshold}. Suggested check: {flag.suggested_check}"
        return "No debris-heavy heuristic flag is currently present for this sample."
    if "saturat" in q or "clipp" in q:
        saturated = [flag for flag in qc_flags if "CLIPPING" in flag.code]
        if not saturated:
            return "No saturation or clipping review flags are currently present."
        channels = ", ".join(sorted({flag.channel or "unknown channel" for flag in saturated}))
        return f"Channels with clipping review flags: {channels}. Inspect histograms before interpreting medians or gates."
    if "compens" in q or "spill" in q:
        return (
            compensation_status(sample)
            + " Compensation is metadata-driven only; raw exported events remain untouched and no compensation wizard is run."
        )
    if "qc" in q or "flags" in q:
        return _qc_answer(qc_flags)
    if "gate" in q:
        if not gates:
            return "No gates are currently defined. Rectangle gates can be added from the Gates tab and are labeled user-defined by default."
        accepted = [gate for gate in gates if not gate.candidate and gate.enabled]
        candidates = [gate for gate in gates if gate.candidate]
        disabled = [gate for gate in gates if not gate.enabled and not gate.candidate]
        names = "; ".join(_gate_phrase(sample, gate) for gate in gates[:8])
        return (
            f"Defined gates: {names}. Accepted/enabled gates: {len(accepted)}; candidate review-needed gates: {len(candidates)}; "
            f"disabled user gates: {len(disabled)}. Candidate gates are suggestions only until accepted or edited."
        )
    if "treated" in q or "control" in q or "compare" in q:
        if not comparison_rows:
            return "No control-versus-treated comparison has been generated yet. Choose groups in the Compare tab."
        summary = comparison_summary(comparison_rows)
        parts = ", ".join(f"{row['label']}: {row['value']} ({row['detail']})" for row in summary)
        return f"Exploratory comparison summary: {parts}. Treat fold-changes and median differences as descriptive until replicate structure is reviewed."
    if "report" in q or "paragraph" in q or "summarize" in q:
        channel_labels = ", ".join(_panel_channel_labels(sample)[:6]) or "no channel labels"
        return (
            f"Sample {sample.sample_id} contains {sample.event_count:,} events across {sample.channel_count} channels. "
            f"Panel/channel context includes {channel_labels}. Current QC status is {qc_summary(qc_flags)}. {len(gates)} gate(s) are defined. "
            "These results are post-acquisition analysis support and require expert cytometry review."
        )
    return (
        f"Sample {sample.sample_id} is loaded with {sample.event_count:,} events and {sample.channel_count} channels. "
        f"Ask about QC flags, selected plots, gates, or control-versus-treated comparisons. {FORBIDDEN_NOTICE}"
    )


def _qc_answer(flags: list[QCFlag]) -> str:
    if not flags:
        return "No QC flags are currently present."
    grouped = {}
    for flag in flags:
        grouped.setdefault(flag.severity, []).append(flag)
    parts = []
    for severity in ("severe", "warning", "info"):
        items = grouped.get(severity, [])
        if items:
            parts.append(f"{severity}: " + "; ".join(f"{flag.code} - {flag.title}" for flag in items[:5]))
    return "QC review summary: " + " | ".join(parts)


def _channel_label(sample: SampleRecord, raw_name: str | None) -> str:
    if not raw_name:
        return "an unselected channel"
    for channel in sample.channels:
        if channel.raw_name == raw_name:
            return channel.label
    return raw_name


def _role_phrase(sample: SampleRecord, raw_name: str | None) -> str:
    if not raw_name:
        return "unselected"
    for channel in sample.channels:
        if channel.raw_name == raw_name:
            marker = f", marker {channel.marker}" if channel.marker else ""
            antibody = f", antibody {channel.antibody}" if channel.antibody else ""
            return f"{channel.role}{marker}{antibody}"
    return "unknown role"


def _gate_phrase(sample: SampleRecord, gate: GateDefinition) -> str:
    channels = ", ".join(_channel_label(sample, channel) for channel in gate.channels)
    state = "candidate review needed" if gate.candidate else ("enabled" if gate.enabled else "disabled")
    return f"{gate.name} ({gate.gate_type} on {channels}; {state})"


def _panel_channel_labels(sample: SampleRecord) -> list[str]:
    labels = []
    for channel in sample.channels:
        if channel.marker or channel.fluorochrome or channel.display_label:
            labels.append(channel.label)
    return labels
