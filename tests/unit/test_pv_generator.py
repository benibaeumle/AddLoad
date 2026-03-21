"""Unit tests for PVGenerator."""

from __future__ import annotations

import numpy as np
import pytest

from src.generators.pv_generator import PVGenerator
from src.models.load_series import PVAParameters


def _default_params(**kwargs) -> PVAParameters:
    defaults = dict(
        peak_power_kwp=10.0,
        azimuth_deg=180.0,
        tilt_deg=30.0,
        climate_zone="central_europe",
    )
    defaults.update(kwargs)
    return PVAParameters(**defaults)


def test_output_shape():
    result = PVGenerator.generate(_default_params(), 2024, seed=0)
    assert result.shape == (35040,)


def test_all_values_non_positive():
    result = PVGenerator.generate(_default_params(), 2024, seed=0)
    assert np.all(result <= 0.0 + 1e-9), f"Positive value found: {result.max()}"


def test_deterministic_with_same_seed():
    r1 = PVGenerator.generate(_default_params(), 2024, seed=42)
    r2 = PVGenerator.generate(_default_params(), 2024, seed=42)
    np.testing.assert_array_equal(r1, r2)


def test_different_seeds_differ():
    r1 = PVGenerator.generate(_default_params(), 2024, seed=1)
    r2 = PVGenerator.generate(_default_params(), 2024, seed=2)
    assert not np.array_equal(r1, r2)


def test_annual_yield_in_range():
    params = _default_params(peak_power_kwp=10.0, azimuth_deg=180.0, tilt_deg=30.0)
    result = PVGenerator.generate(params, 2024, seed=0)
    annual_yield_per_kwp = abs(result.sum()) * 0.25 / params.peak_power_kwp
    assert 900 <= annual_yield_per_kwp <= 1100, (
        f"Annual yield {annual_yield_per_kwp:.1f} kWh/kWp outside [900, 1100]"
    )


def test_negative_peak_power_raises():
    params = _default_params(peak_power_kwp=-1.0)
    with pytest.raises(ValueError, match="peak_power_kwp"):
        PVGenerator.generate(params, 2024, seed=0)


def test_zero_peak_power_returns_zeros():
    params = _default_params(peak_power_kwp=0.0)
    result = PVGenerator.generate(params, 2024, seed=0)
    assert np.all(result == 0.0)
