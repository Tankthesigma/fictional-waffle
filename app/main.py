from __future__ import annotations

from pathlib import Path
import sys
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(PROJECT_ROOT))

from dash import Dash  # noqa: E402

from app.core.paths import ensure_runtime_dirs  # noqa: E402
from app.core.session_store import WorkbenchSession  # noqa: E402
from app.ui.callbacks import register_callbacks  # noqa: E402
from app.ui.layout import build_layout  # noqa: E402


def create_app() -> Dash:
    """Create the local Dash app."""
    try:
        import PIL.Image  # noqa: F401
    except Exception:
        pass
    ensure_runtime_dirs()
    dash_app = Dash(__name__, title="Ask Flow Workbench", suppress_callback_exceptions=True)
    dash_app.layout = build_layout()
    register_callbacks(dash_app, WorkbenchSession())
    return dash_app


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("ASK_FLOW_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(debug=debug, host="127.0.0.1", port=8050)
