"""Integration test: SC-004 — BESS constraints at all 35040 steps."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from src.generators.bess_simulator import BESSSimulator
from src.generators.slp_generator import SLPGenerator
from src.models.load_series import BESSParameters, BESSStrategy, SLPParameters


@pytest.fixture
def bdew_profiles():
    """Load BDEW profiles for tests."""
    bdew_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "bdew"
    )
    profiles = {}
    for name in ["H0"]:
        path = os.path.join(bdew_dir, f"{name}.csv")
        if os.path.exists(path):
            profiles[name] = pd.read_csv(path)
    return profiles


@pytest.fixture
def slp_net_load(bdew_profiles):
    """Generate a realistic net load from H0 SLP."""
    params = SLPParameters(profile_type="H0", annual_energy_kwh=10000.0)
    return SLPGenerator.generate(params, 2024, bdew_profiles)


def test_bess_power_constraints(slp_net_load):
    """BESS dispatch never exceeds max charge/discharge power."""
    params = BESSParameters(
        capacity_kwh=100.0,
        max_charge_power_kw=50.0,
        max_discharge_power_kw=50.0,
        efficiency_pct=90.0,
        strategy=BESSStrategy.PEAK_SHAVING,
    )
    result = BESSSimulator.simulate(params, slp_net_load)

    assert result.shape == (35040,)
    assert np.all(result <= params.max_charge_power_kw + 1e-6), (
        f"Charge exceeded: max={result.max():.4f}"
    )
    assert np.all(result >= -params.max_discharge_power_kw - 1e-6), (
        f"Discharge exceeded: min={result.min():.4f}"
    )


def test_bess_peak_not_worsened(slp_net_load):
    """Peak shaving must not worsen the original peak."""
    params = BESSParameters(
        capacity_kwh=100.0,
        max_charge_power_kw=50.0,
        max_discharge_power_kw=50.0,
        efficiency_pct=90.0,
        strategy=BESSStrategy.PEAK_SHAVING,
    )
    bess = BESSSimulator.simulate(params, slp_net_load)
    new_peak = (slp_net_load + bess).max()
    old_peak = slp_net_load.max()
    assert new_peak <= old_peak + 1e-6, (
        f"Peak worsened: old={old_peak:.4f}, new={new_peak:.4f}"
    )


def test_bess_output_length(slp_net_load):
    """BESS output must have exactly 35040 steps."""
    params = BESSParameters(
        capacity_kwh=100.0,
        max_charge_power_kw=50.0,
        max_discharge_power_kw=50.0,
        efficiency_pct=90.0,
        strategy=BESSStrategy.EIGENVERBRAUCH,
    )
    result = BESSSimulator.simulate(params, slp_net_load)
    assert len(result) == 35040
