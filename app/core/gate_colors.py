from __future__ import annotations

import hashlib

GATE_PALETTE = ["#2D7DD2", "#EB6534", "#16A085", "#8E44AD", "#F39C12", "#C0392B", "#27AE60", "#2C3E50"]


def gate_color(gate_id: str) -> str:
    """Return a deterministic display color for a gate id."""
    digest = hashlib.sha256(gate_id.encode("utf-8")).digest()
    return GATE_PALETTE[digest[0] % len(GATE_PALETTE)]
