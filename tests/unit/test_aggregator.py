"""Unit tests for Aggregator."""

from __future__ import annotations

import uuid

import numpy as np
import pytest

from src.aggregator import Aggregator
from src.models.load_series import LoadSeries, SLPParameters
from src.models.project import SeriesType
from src.services.project_service import ProjectService


def _make_project_with_series(values_list: list[tuple[SeriesType, list]]):
    project = ProjectService.create(
        kunde="Test", ersteller="Dev", adresse="Teststr.", seed=0
    )
    for stype, vals in values_list:
        params = SLPParameters(profile_type="H0", annual_energy_kwh=1000.0)
        series = LoadSeries(
            id=str(uuid.uuid4()),
            name=f"{stype.value}_series",
            series_type=stype,
            parameters=params,
            values=vals,
        )
        project.load_series.append(series)
    return project


def test_empty_project_returns_zeros():
    project = ProjectService.create(
        kunde="Test", ersteller="Dev", adresse="Teststr.", seed=0
    )
    result = Aggregator.compute(project)
    assert result.df.shape[0] == 35040
    assert np.all(result.total == 0.0)
    assert result.peak_kw == 0.0
    assert result.valley_kw == 0.0


def test_single_slp_series():
    vals = np.ones(35040).tolist()
    project = _make_project_with_series([(SeriesType.SLP, vals)])
    result = Aggregator.compute(project)
    assert np.allclose(result.category_sums["SLP_SUM"], 1.0)
    assert np.allclose(result.total, 1.0)
    assert result.peak_kw == pytest.approx(1.0)


def test_total_is_sum_of_categories():
    vals = np.ones(35040).tolist()
    project = _make_project_with_series([
        (SeriesType.SLP, vals),
        (SeriesType.CSV, vals),
    ])
    result = Aggregator.compute(project)
    expected = result.category_sums["SLP_SUM"] + result.category_sums["CSV_SUM"]
    np.testing.assert_allclose(result.total, expected)


def test_inactive_series_excluded():
    vals = np.ones(35040).tolist()
    project = _make_project_with_series([(SeriesType.SLP, vals)])
    project.load_series[0].is_active = False
    result = Aggregator.compute(project)
    assert np.all(result.total == 0.0)


def test_wrong_shape_raises():
    project = ProjectService.create(
        kunde="Test", ersteller="Dev", adresse="Teststr.", seed=0
    )
    params = SLPParameters(profile_type="H0", annual_energy_kwh=1000.0)
    series = LoadSeries(
        id=str(uuid.uuid4()),
        name="bad",
        series_type=SeriesType.SLP,
        parameters=params,
        values=[1.0, 2.0],
    )
    project.load_series.append(series)
    with pytest.raises(ValueError):
        Aggregator.compute(project)


def test_no_nan_in_result():
    vals = np.ones(35040).tolist()
    project = _make_project_with_series([(SeriesType.SLP, vals)])
    result = Aggregator.compute(project)
    assert not result.df.isna().any().any()
