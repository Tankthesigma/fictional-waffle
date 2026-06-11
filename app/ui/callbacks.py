from __future__ import annotations

from app.core.session_store import WorkbenchSession
from app.ui.callbacks_ask_flow import register_ask_flow_callbacks
from app.ui.callbacks_compare import register_compare_callbacks
from app.ui.callbacks_gating import register_gating_callbacks
from app.ui.callbacks_plots import register_plot_callbacks
from app.ui.callbacks_qc import register_qc_callbacks
from app.ui.callbacks_reports import register_report_callbacks
from app.ui.callbacks_sample import register_sample_callbacks
from app.ui.callbacks_templates import register_template_callbacks
from app.ui.callbacks_upload import register_upload_callbacks
from app.ui.callbacks_workflow import register_workflow_callbacks


def register_callbacks(app, session: WorkbenchSession) -> None:
    register_upload_callbacks(app, session)
    register_sample_callbacks(app, session)
    register_plot_callbacks(app, session)
    register_gating_callbacks(app, session)
    register_compare_callbacks(app, session)
    register_qc_callbacks(app, session)
    register_report_callbacks(app, session)
    register_ask_flow_callbacks(app, session)
    register_workflow_callbacks(app, session)
    register_template_callbacks(app, session)
