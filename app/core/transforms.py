from __future__ import annotations

import numpy as np
import pandas as pd


def raw_transform(values: np.ndarray | pd.Series) -> np.ndarray:
    """Return values as a floating-point NumPy array without changing scale."""
    return np.asarray(values, dtype=float)


def safe_log10(values: np.ndarray | pd.Series, floor: float = 1.0) -> np.ndarray:
    """Apply a display-safe log10 transform without mutating source data."""
    arr = np.asarray(values, dtype=float)
    safe = np.where(np.isfinite(arr), arr, np.nan)
    safe = np.where(safe > floor, safe, floor)
    return np.log10(safe)


def arcsinh_transform(values: np.ndarray | pd.Series, cofactor: float = 150.0) -> np.ndarray:
    """Apply an arcsinh display transform with a configurable cofactor."""
    if cofactor <= 0:
        raise ValueError("cofactor must be positive")
    arr = np.asarray(values, dtype=float)
    return np.arcsinh(arr / cofactor)


def apply_transform(
    values: np.ndarray | pd.Series,
    transform: str = "raw",
    *,
    cofactor: float = 150.0,
    log_floor: float = 1.0,
) -> np.ndarray:
    """Dispatch a supported display transform."""
    if transform in {"raw", "linear"}:
        return raw_transform(values)
    if transform in {"log", "log10", "safe_log10"}:
        return safe_log10(values, floor=log_floor)
    if transform == "arcsinh":
        return arcsinh_transform(values, cofactor=cofactor)
    if transform == "logicle":
        try:
            from flowutils.transforms import logicle  # type: ignore

            arr = np.asarray(values, dtype=float)
            return logicle(arr, channel_indices=None)
        except Exception as exc:  # pragma: no cover - depends on optional compiled package API
            raise ValueError("logicle transform is unavailable in this environment") from exc
    raise ValueError(f"unsupported transform: {transform}")
