from app.ui.callbacks_workflow import _analysis_guide


def _guide_text(component) -> str:
    return str(component.to_plotly_json())


def test_analysis_guide_empty_project_points_to_import_and_waiting_compare():
    guide = _analysis_guide(
        sample_count=0,
        selected_sample=None,
        gate_count=0,
        accepted_gate_count=0,
        candidate_gate_count=0,
        qc_flag_count=0,
        comparison_count=0,
    )

    text = _guide_text(guide)

    assert "Next-step checklist" in text
    assert "Upload exported FCS or event-level CSV files" in text
    assert "waiting" in text
    assert "failed" not in text.lower()


def test_analysis_guide_surfaces_qc_candidate_gate_and_report_readiness():
    guide = _analysis_guide(
        sample_count=3,
        selected_sample="s1",
        gate_count=1,
        accepted_gate_count=0,
        candidate_gate_count=1,
        qc_flag_count=2,
        comparison_count=4,
    )

    text = _guide_text(guide)

    assert "2 QC review flag(s)" in text
    assert "1 candidate gate(s) need accept/edit/reject" in text
    assert "4 exploratory comparison row(s)" in text
    assert "Ready for local PDF/PPTX export" in text
