"""Integration test: SC-003 — SLP annual sum ±0.1%."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from src.generators.slp_generator import SLPGenerator
from src.models.load_series import SLPParameters


@pytest.fixture
def bdew_profiles():
    """Load BDEW profiles for tests."""
    bdew_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "bdew"
    )
    profiles = {}
    for name in ["H0", "G0", "G1", "G2", "G3", "G4", "G5", "G6", "L0", "L1", "L2"]:
        path = os.path.join(bdew_dir, f"{name}.csv")
        if os.path.exists(path):
            profiles[name] = pd.read_csv(path)
    return profiles


@pytest.mark.parametrize(
    "profile_type,annual_kwh",
    [
        ("H0", 5000.0),
        ("G0", 10000.0),
        ("G1", 8000.0),
        ("L0", 3000.0),
    ],
)
def test_slp_integral(bdew_profiles, profile_type, annual_kwh):
    """SLP values.sum() * 0.25 ≈ annual_kwh within ±0.1%."""
    params = SLPParameters(profile_type=profile_type, annual_energy_kwh=annual_kwh)
    values = SLPGenerator.generate(params, 2024, bdew_profiles)

    assert values.shape == (35040,)
    computed = values.sum() * 0.25
    rel_error = abs(computed - annual_kwh) / annual_kwh
    assert rel_error < 0.001, (
        f"{profile_type}: integral={computed:.2f}, expected={annual_kwh:.2f}, "
        f"relative error={rel_error:.4%}"
    )


def test_slp_all_non_negative(bdew_profiles):
    """All SLP values must be >= 0."""
    params = SLPParameters(profile_type="H0", annual_energy_kwh=5000.0)
    values = SLPGenerator.generate(params, 2024, bdew_profiles)
    assert np.all(values >= 0), f"Found negative values: {values[values < 0]}"


def test_slp_correct_length(bdew_profiles):
    """SLP output must have exactly 35040 steps."""
    params = SLPParameters(profile_type="H0", annual_energy_kwh=5000.0)
    values = SLPGenerator.generate(params, 2024, bdew_profiles)
    assert len(values) == 35040
