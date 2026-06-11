import numpy as np
import pytest

from app.core.transforms import arcsinh_transform, safe_log10


def test_safe_log_transform_clamps_non_positive_values():
    values = np.array([-10.0, 0.0, 1.0, 100.0])

    transformed = safe_log10(values)

    assert np.all(np.isfinite(transformed))
    assert transformed.tolist() == [0.0, 0.0, 0.0, 2.0]


def test_arcsinh_transform_uses_cofactor():
    values = np.array([0.0, 150.0])

    transformed = arcsinh_transform(values, cofactor=150.0)

    assert transformed[0] == 0.0
    assert transformed[1] == pytest.approx(np.arcsinh(1.0))
