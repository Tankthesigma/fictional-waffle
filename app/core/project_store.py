from __future__ import annotations

import json
from pathlib import Path

from app.models.project_schema import ProjectState


def save_project(project: ProjectState, path: str | Path) -> Path:
    """Save project metadata without embedding raw event matrices."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
    return target


def load_project(path: str | Path) -> ProjectState:
    """Load saved project metadata."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("project JSON must contain an object")
    return ProjectState.from_dict(payload)
