from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def export_rows_csv(rows: list[dict[str, Any]], path: str | Path) -> Path:
    """Export table rows to CSV, preserving an empty file with headers when possible."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(target, index=False)
    return target
