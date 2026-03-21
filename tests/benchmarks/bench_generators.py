"""Benchmark: PERF-002 — chart update <= 1 s for <= 10 series."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def bdew_profiles():
    bdew_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "bdew"
    )
    profiles = {}
    for name in ["H0", "G0", "G1"]:
        path = os.path.join(bdew_dir, f"{name}.csv")
        if os.path.exists(path):
            profiles[name] = pd.read_csv(path)
    return profiles


def test_slp_generate_benchmark(benchmark, bdew_profiles):
    """SLP generation for one series must complete quickly."""
    from src.generators.slp_generator import SLPGenerator
    from src.models.load_series import SLPParameters

    params = SLPParameters(profile_type="H0", annual_energy_kwh=5000.0)

    result = benchmark(SLPGenerator.generate, params, 2024, bdew_profiles)
    assert result.shape == (35040,)
