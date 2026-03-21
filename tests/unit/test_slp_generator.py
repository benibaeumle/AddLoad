"""Unit tests for SLPGenerator."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from src.generators.slp_generator import SLPGenerator
from src.models.load_series import SLPParameters


@pytest.fixture(scope="module")
def bdew_profiles():
    bdew_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "bdew"
    )
    profiles = {}
    for name in ["H0", "G0", "G1", "G2", "G3", "G4", "G5", "G6", "L0", "L1", "L2"]:
        path = os.path.join(bdew_dir, f"{name}.csv")
        if os.path.exists(path):
            profiles[name] = pd.read_csv(path)
    return profiles


def test_generate_shape(bdew_profiles):
    params = SLPParameters(profile_type="H0", annual_energy_kwh=5000.0)
    result = SLPGenerator.generate(params, 2024, bdew_profiles)
    assert result.shape == (35040,)


def test_generate_non_negative(bdew_profiles):
    params = SLPParameters(profile_type="H0", annual_energy_kwh=5000.0)
    result = SLPGenerator.generate(params, 2024, bdew_profiles)
    assert np.all(result >= 0)


def test_generate_integral(bdew_profiles):
    annual_kwh = 5000.0
    params = SLPParameters(profile_type="H0", annual_energy_kwh=annual_kwh)
    result = SLPGenerator.generate(params, 2024, bdew_profiles)
    integral = result.sum() * 0.25
    assert abs(integral - annual_kwh) / annual_kwh < 0.001


def test_generate_zero_energy(bdew_profiles):
    params = SLPParameters(profile_type="H0", annual_energy_kwh=0.0)
    result = SLPGenerator.generate(params, 2024, bdew_profiles)
    assert np.all(result == 0.0)


def test_generate_missing_profile_raises(bdew_profiles):
    params = SLPParameters(profile_type="XX", annual_energy_kwh=1000.0)
    with pytest.raises(KeyError):
        SLPGenerator.generate(params, 2024, bdew_profiles)


@pytest.mark.parametrize("profile", ["G0", "G1", "L0"])
def test_generate_other_profiles(bdew_profiles, profile):
    params = SLPParameters(profile_type=profile, annual_energy_kwh=3000.0)
    result = SLPGenerator.generate(params, 2024, bdew_profiles)
    assert result.shape == (35040,)
    assert np.all(result >= 0)
