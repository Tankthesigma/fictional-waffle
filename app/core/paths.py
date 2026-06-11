from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = PROJECT_ROOT / "app_data" / "uploads"
EXPORT_ROOT = PROJECT_ROOT / "exports"
GATES_PATH = EXPORT_ROOT / "gates.json"
PROJECT_PATH = EXPORT_ROOT / "ask-flow-project.json"


def ensure_runtime_dirs() -> None:
    """Create local runtime directories under the project root."""
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
