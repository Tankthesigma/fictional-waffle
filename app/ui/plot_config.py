from __future__ import annotations

PLOT_CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"],
    "toImageButtonOptions": {"format": "png", "scale": 3},
}

GATING_CONFIG = {
    **PLOT_CONFIG,
    "modeBarButtonsToAdd": ["drawrect", "drawclosedpath", "eraseshape"],
}
