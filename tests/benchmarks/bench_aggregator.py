"""Benchmark: PERF-004 — aggregation at 10 x 35040 steps."""

from __future__ import annotations

import uuid

import numpy as np
import pytest

from src.aggregator import Aggregator
from src.models.load_series import LoadSeries, SLPParameters
from src.models.project import SeriesType
from src.services.project_service import ProjectService


@pytest.fixture
def project_10_series():
    """Project with 10 pre-computed SLP series."""
    project = ProjectService.create(
        kunde="Benchmark", ersteller="Test", adresse="Benchmarkstr.", seed=0
    )
    rng = np.random.default_rng(42)
    for i in range(10):
        values = rng.uniform(0, 50, 35040).tolist()
        params = SLPParameters(profile_type="H0", annual_energy_kwh=5000.0)
        series = LoadSeries(
            id=str(uuid.uuid4()),
            name=f"Series {i}",
            series_type=SeriesType.SLP,
            parameters=params,
            values=values,
        )
        project.load_series.append(series)
    return project


def test_aggregator_benchmark(benchmark, project_10_series):
    """Aggregation of 10 series must complete quickly."""
    result = benchmark(Aggregator.compute, project_10_series)
    assert result.df.shape[0] == 35040
