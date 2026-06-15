from __future__ import annotations

import ast
import operator
import re

from app.core.compare import comparison_insights, comparison_summary
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
    general = _general_answer(q)
    if general:
        return general
    if not sample:
        return "Upload or select a sample first. " + FORBIDDEN_NOTICE
    if any(token in q for token in ("plan", "what next", "next step", "workup", "analyze this", "analysis")):
        return _analysis_plan_answer(sample, gates, qc_flags, comparison_rows)
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


def _general_answer(q: str) -> str | None:
    """Answer small local questions that do not need uploaded cytometry data."""
    if not q:
        return None
    if re.fullmatch(r"(hi|hello|hey|yo|sup|what'?s up|whats up)[!. ]*", q):
        return (
            "Hey. I am here. Load an FCS/CSV file or the demo dataset and I can run QC, set plots, "
            "create review-needed gates, approve/reject candidates, and summarize results."
        )
    math_answer = _arithmetic_answer(q)
    if math_answer:
        return math_answer
    if any(phrase in q for phrase in ("what can you do", "help", "skills", "commands")):
        return (
            "I can navigate the workbench, set scatter/histogram plots, switch transforms, run QC review, "
            "create review-needed gates, run cluster-guided gates, approve/reject candidate gates, and draft local summaries. "
            "Upload or select a sample for cytometry-specific analysis."
        )
    return None


def _arithmetic_answer(q: str) -> str | None:
    expression = q
    expression = re.sub(r"\b(what'?s|what is|calculate|calc|solve|equals?|please|answer)\b", " ", expression)
    expression = expression.replace("x", "*").replace("×", "*").replace("÷", "/")
    expression = re.sub(r"\s+", "", expression)
    if not expression or not re.fullmatch(r"[0-9+\-*/().]+", expression):
        return None
    try:
        value = _eval_arithmetic(ast.parse(expression, mode="eval").body)
    except Exception:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{expression} = {value}"


def _eval_arithmetic(node: ast.AST) -> float:
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_arithmetic(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in operators:
        left = _eval_arithmetic(node.left)
        right = _eval_arithmetic(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ValueError("division by zero")
        return operators[type(node.op)](left, right)
    raise ValueError("unsupported expression")


def analysis_briefing(
    sample: SampleRecord | None,
    *,
    x_channel: str | None = None,
    y_channel: str | None = None,
    gates: list[GateDefinition] | None = None,
    qc_flags: list[QCFlag] | None = None,
    comparison_rows: list[dict[str, object]] | None = None,
) -> list[dict[str, str]]:
    """Build a deterministic local briefing for the Ask Flow tab."""
    gates = gates or []
    qc_flags = qc_flags or []
    comparison_rows = comparison_rows or []
    if sample is None:
        return [
            {
                "status": "waiting",
                "title": "No Active Sample",
                "body": "Upload FCS or event-level CSV files to generate a local analysis briefing.",
                "detail": "Ask Flow stays local and deterministic.",
            }
        ]

    enabled = [gate for gate in gates if gate.enabled and not gate.candidate]
    candidates = [gate for gate in gates if gate.candidate]
    disabled = [gate for gate in gates if not gate.enabled and not gate.candidate]
    severities = _severity_counts(qc_flags)
    top_qc = _top_qc_flag(qc_flags)
    compare_note = comparison_insights(comparison_rows)[1] if comparison_rows else None
    return [
        {
            "status": "info",
            "title": "Active Context",
            "body": f"{sample.sample_id}: {sample.event_count:,} events, {sample.channel_count} channels, plot {_channel_label(sample, x_channel)} x {_channel_label(sample, y_channel)}.",
            "detail": f"Panel labels visible: {len(_panel_channel_labels(sample))}; compensation view depends on the plot setting.",
        },
        {
            "status": "review" if qc_flags else "info",
            "title": "QC Brief",
            "body": f"{qc_summary(qc_flags)} ({severities['severe']} severe, {severities['warning']} warning, {severities['info']} info).",
            "detail": top_qc or "No rule-based QC review flags are currently present.",
        },
        {
            "status": "review" if candidates else "info",
            "title": "Gate Brief",
            "body": f"{len(enabled)} enabled user/review gate(s), {len(candidates)} candidate gate(s), {len(disabled)} disabled gate(s).",
            "detail": "Candidate or quick-review gates should be edited or accepted by a human before final reporting.",
        },
        {
            "status": "review" if comparison_rows else "waiting",
            "title": "Comparison Brief",
            "body": compare_note["message"] if compare_note else "No control-versus-treated comparison has been generated yet.",
            "detail": compare_note["detail"] if compare_note else "Use the Compare tab after group labels are assigned.",
        },
        {
            "status": "boundary",
            "title": "Safety Boundary",
            "body": "Local post-acquisition analysis support only.",
            "detail": FORBIDDEN_NOTICE,
        },
    ]


def analysis_plan(
    sample: SampleRecord | None,
    *,
    gates: list[GateDefinition] | None = None,
    qc_flags: list[QCFlag] | None = None,
    comparison_rows: list[dict[str, object]] | None = None,
) -> list[dict[str, str]]:
    """Build a state-aware suggested analysis plan."""
    gates = gates or []
    qc_flags = qc_flags or []
    comparison_rows = comparison_rows or []
    if sample is None:
        return [
            {
                "status": "waiting",
                "title": "Load Data",
                "body": "Upload FCS files or load the demo dataset.",
                "detail": "The assistant needs event-level data before it can suggest analysis steps.",
            }
        ]

    plan = [
        {
            "status": "ready",
            "title": "1. Review Acquisition Shape",
            "body": "Start with FSC/SSC and Time context before fluorescence interpretation.",
            "detail": f"{sample.event_count:,} events across {sample.channel_count} channels are loaded.",
        }
    ]
    severe_or_warning = [flag for flag in qc_flags if flag.severity in {"severe", "warning"}]
    if severe_or_warning:
        top = sorted(severe_or_warning, key=lambda flag: 0 if flag.severity == "severe" else 1)[0]
        plan.append(
            {
                "status": "review",
                "title": "2. Resolve QC Review Items",
                "body": f"Inspect {top.title.lower()} before leaning on gates or medians.",
                "detail": top.suggested_check,
            }
        )
    else:
        plan.append(
            {
                "status": "ready",
                "title": "2. QC Looks Clear",
                "body": "No severe or warning QC flags are currently active.",
                "detail": "Still review histograms and scatter shape manually.",
            }
        )
    accepted = [gate for gate in gates if gate.enabled and not gate.candidate]
    candidates = [gate for gate in gates if gate.candidate]
    if not accepted:
        plan.append(
            {
                "status": "waiting",
                "title": "3. Create A Review Gate",
                "body": "Add a current-view or rectangle gate, then inspect gate statistics.",
                "detail": "Candidate gates remain review-needed until accepted or edited.",
            }
        )
    else:
        plan.append(
            {
                "status": "ready",
                "title": "3. Check Gate Statistics",
                "body": f"{len(accepted)} enabled gate(s) are ready for counts and fluorescence summaries.",
                "detail": f"{len(candidates)} candidate gate(s) still need review." if candidates else "No candidate gates are pending.",
            }
        )
    if sample.condition and comparison_rows:
        plan.append(
            {
                "status": "ready",
                "title": "4. Interpret Batch Differences",
                "body": "Control-versus-treated rows are available for exploratory review.",
                "detail": "Use median differences first; fold-change is guarded when values are negative or near zero.",
            }
        )
    elif sample.condition:
        plan.append(
            {
                "status": "waiting",
                "title": "4. Run Comparison",
                "body": "Group labels exist; choose control and treated groups in Compare.",
                "detail": "Stats are descriptive until replicate structure is reviewed.",
            }
        )
    else:
        plan.append(
            {
                "status": "waiting",
                "title": "4. Add Group Labels",
                "body": "Upload a manifest or label conditions before comparison.",
                "detail": "Condition and replicate labels make batch review cleaner.",
            }
        )
    plan.append(
        {
            "status": "ready",
            "title": "5. Export A Clean Report",
            "body": "Export PDF or PowerPoint after plots, gates, QC, and comparison are reviewed.",
            "detail": "Reports retain the post-acquisition and expert-review disclaimer.",
        }
    )
    return plan


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


def _analysis_plan_answer(
    sample: SampleRecord,
    gates: list[GateDefinition],
    qc_flags: list[QCFlag],
    comparison_rows: list[dict[str, object]],
) -> str:
    rows = analysis_plan(sample, gates=gates, qc_flags=qc_flags, comparison_rows=comparison_rows)
    return "Suggested analysis plan:\n" + "\n".join(f"{row['title']}: {row['body']} {row['detail']}" for row in rows)


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


def _severity_counts(flags: list[QCFlag]) -> dict[str, int]:
    return {
        "severe": sum(flag.severity == "severe" for flag in flags),
        "warning": sum(flag.severity == "warning" for flag in flags),
        "info": sum(flag.severity == "info" for flag in flags),
    }


def _top_qc_flag(flags: list[QCFlag]) -> str:
    priority = {"severe": 0, "warning": 1, "info": 2}
    if not flags:
        return ""
    flag = sorted(flags, key=lambda item: priority.get(item.severity, 99))[0]
    channel = f" on {flag.channel}" if flag.channel else ""
    return f"Top review flag: {flag.title}{channel}; suggested check: {flag.suggested_check}"
