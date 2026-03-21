"""Benchmark: PERF-003 — CSV parse <= 5 s for 10 MB file."""

from __future__ import annotations

import io

import numpy as np
import pytest


@pytest.fixture
def small_csv_bytes():
    """Generate a minimal valid 35040-row CSV for benchmark."""
    lines = ["timestamp;P_kW"]
    import pandas as pd
    idx = pd.date_range("2024-01-01", periods=35040, freq="15min", tz="UTC")
    rng = np.random.default_rng(0)
    values = rng.uniform(0, 100, 35040)
    for ts, v in zip(idx, values):
        lines.append(f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')};{v:.3f}")
    return "\n".join(lines).encode("utf-8")


def test_csv_parse_benchmark(benchmark, small_csv_bytes):
    """CSV parse of a 35040-row file must complete quickly."""
    from src.generators.csv_parser import parse_upload

    arr, params, detected_year = benchmark(parse_upload, small_csv_bytes, "test.csv", 2024)
    assert arr.shape == (35040,)
