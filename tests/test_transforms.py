import numpy as np
import pytest

from app.core.transforms import apply_transform, arcsinh_transform, invert_transform, log10_clamp_warning, log10_clamped_fraction, safe_log10


def test_safe_log_transform_clamps_non_positive_values():
    values = np.array([-10.0, 0.0, 1.0, 100.0])

    transformed = safe_log10(values)

    assert np.all(np.isfinite(transformed))
    assert transformed.tolist() == [0.0, 0.0, 0.0, 2.0]
    assert log10_clamped_fraction(values) == pytest.approx(75.0)
    assert "75.0%" in log10_clamp_warning("FL1-A", values)


def test_arcsinh_transform_uses_cofactor():
    values = np.array([0.0, 150.0])

    transformed = arcsinh_transform(values, cofactor=150.0)

    assert transformed[0] == 0.0
    assert transformed[1] == pytest.approx(np.arcsinh(1.0))


def test_logicle_transform_round_trips_for_drawn_gate_coordinates():
    raw = np.array([-100.0, 0.0, 1000.0, 10000.0])

    display = apply_transform(raw, "logicle")
    restored = invert_transform(display, "logicle")

    np.testing.assert_allclose(restored, raw, rtol=1e-9, atol=1e-7)
