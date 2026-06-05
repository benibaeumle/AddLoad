"""Unit tests for BESSSimulator."""

from __future__ import annotations

import numpy as np
import pytest

from src.generators.bess_simulator import BESSSimulator
from src.models.load_series import BESSParameters, BESSStrategy


def _default_params(**kwargs) -> BESSParameters:
    defaults = dict(
        capacity_kwh=100.0,
        max_charge_power_kw=50.0,
        max_discharge_power_kw=50.0,
        efficiency_pct=90.0,
        strategy=BESSStrategy.PEAK_SHAVING,
        peak_shaving_threshold_kw=None,
    )
    defaults.update(kwargs)
    return BESSParameters(**defaults)


def _flat_net_load(value: float = 30.0) -> np.ndarray:
    return np.full(35040, value, dtype=float)


def test_output_shape():
    params = _default_params()
    net = _flat_net_load()
    result = BESSSimulator.simulate(params, net)
    assert result.shape == (35040,)


def test_wrong_shape_raises():
    params = _default_params()
    net = np.ones(100)
    with pytest.raises(ValueError, match="35040"):
        BESSSimulator.simulate(params, net)


def test_zero_capacity_raises():
    params = _default_params(capacity_kwh=0.0)
    with pytest.raises(ValueError):
        BESSSimulator.simulate(params, _flat_net_load())


def test_zero_charge_power_raises():
    params = _default_params(max_charge_power_kw=0.0)
    with pytest.raises(ValueError):
        BESSSimulator.simulate(params, _flat_net_load())


def test_power_limits_respected():
    params = _default_params(
        max_charge_power_kw=20.0,
        max_discharge_power_kw=30.0,
        peak_shaving_threshold_kw=25.0,
    )
    net = np.tile(
        np.concatenate([np.full(16, 10.0), np.full(16, 50.0)]),
        35040 // 32,
    ).astype(float)
    result = BESSSimulator.simulate(params, net)
    assert np.all(result <= 20.0 + 1e-6)
    assert np.all(result >= -30.0 - 1e-6)


def test_eigenverbrauch_strategy():
    params = _default_params(strategy=BESSStrategy.EIGENVERBRAUCH)
    net = _flat_net_load(10.0)
    result = BESSSimulator.simulate(params, net)
    assert result.shape == (35040,)


def test_arbitrage_strategy():
    params = _default_params(strategy=BESSStrategy.ARBITRAGE)
    net = _flat_net_load(20.0)
    result = BESSSimulator.simulate(params, net)
    assert result.shape == (35040,)
    slot_3am = 12
    assert result[slot_3am] >= 0.0 - 1e-6

    slot_6pm = 72
    assert result[slot_6pm] <= 0.0 + 1e-6


def test_peak_shaving_auto_threshold():
    rng = np.random.default_rng(0)
    net = rng.uniform(0, 100, 35040).astype(float)
    params = _default_params(strategy=BESSStrategy.PEAK_SHAVING, peak_shaving_threshold_kw=None)
    result = BESSSimulator.simulate(params, net)
    assert result.shape == (35040,)


def test_peak_shaving_nonzero_output():
    net = np.tile(
        np.concatenate([np.full(16, 10.0), np.full(16, 40.0)]),
        35040 // 32,
    ).astype(float)
    params = _default_params(
        strategy=BESSStrategy.PEAK_SHAVING,
        peak_shaving_threshold_kw=25.0,
    )
    result = BESSSimulator.simulate(params, net)
    assert np.any(result != 0.0), "Peak shaving should produce non-zero dispatch"
    assert np.any(result < 0.0), "Peak shaving should discharge when load > threshold"
    assert np.any(result > 0.0), "Peak shaving should charge when load < threshold"
