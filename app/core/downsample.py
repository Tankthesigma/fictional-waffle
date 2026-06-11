from __future__ import annotations

import numpy as np
import pandas as pd


def downsample_events(
    events: pd.DataFrame,
    max_events: int = 50_000,
    random_state: int = 42,
) -> pd.DataFrame:
    """Return a deterministic display-sized subset of events."""
    if max_events <= 0:
        raise ValueError("max_events must be positive")
    if len(events) <= max_events:
        return events.copy()
    rng = np.random.default_rng(random_state)
    selected = rng.choice(len(events), size=max_events, replace=False)
    selected.sort()
    return events.iloc[selected].copy()
