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


def log10_clamped_fraction(values: np.ndarray | pd.Series, floor: float = 1.0) -> float:
    """Return the percent of finite values that would be clamped by safe_log10."""
    arr = np.asarray(values, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return 0.0
    return float(np.mean(finite <= floor) * 100.0)


def log10_clamp_warning(channel: str, values: np.ndarray | pd.Series, floor: float = 1.0) -> str | None:
    """Build a plain-English warning when safe_log10 floors real values."""
    fraction = log10_clamped_fraction(values, floor=floor)
    if fraction <= 0:
        return None
    return f"{channel}: {fraction:.1f}% of finite events were clamped at the log10 floor ({floor:g})."


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


def invert_transform(
    values: np.ndarray | pd.Series | list[float],
    transform: str = "raw",
    *,
    cofactor: float = 150.0,
) -> np.ndarray:
    """Map display coordinates back to raw event coordinates for gate storage."""
    arr = np.asarray(values, dtype=float)
    if transform in {"raw", "linear"}:
        return arr
    if transform in {"log", "log10", "safe_log10"}:
        return np.power(10.0, arr)
    if transform == "arcsinh":
        if cofactor <= 0:
            raise ValueError("cofactor must be positive")
        return np.sinh(arr) * cofactor
    if transform == "logicle":
        raise ValueError("drawn gates cannot be converted from logicle display yet; use raw, log10, or arcsinh")
    raise ValueError(f"unsupported transform: {transform}")
