"""Unit tests for LoadRegistry."""

from __future__ import annotations

import uuid

import numpy as np
import pytest

from src.models.load_series import BESSParameters, BESSStrategy, LoadSeries, SLPParameters
from src.models.project import SeriesType
from src.services.load_registry import LoadRegistry
from src.services.project_service import ProjectService


def _make_project():
    return ProjectService.create(kunde="Test", ersteller="Dev", adresse="Teststr.", seed=0)


def _make_series(series_type=SeriesType.SLP, value=1.0, name="S") -> LoadSeries:
    params = SLPParameters(profile_type="H0", annual_energy_kwh=1000.0)
    return LoadSeries(
        id=str(uuid.uuid4()),
        name=name,
        series_type=series_type,
        parameters=params,
        values=np.full(35040, value, dtype=float).tolist(),
        is_active=True,
    )


def test_add_series():
    project = _make_project()
    series = _make_series()
    LoadRegistry.add(project, series)
    assert len(project.load_series) == 1
    assert project.load_series[0].id == series.id


def test_add_duplicate_raises():
    project = _make_project()
    series = _make_series()
    LoadRegistry.add(project, series)
    with pytest.raises(ValueError, match="existiert bereits"):
        LoadRegistry.add(project, series)


def test_remove_series():
    project = _make_project()
    series = _make_series()
    LoadRegistry.add(project, series)
    LoadRegistry.remove(project, series.id)
    assert len(project.load_series) == 0


def test_remove_nonexistent_raises():
    project = _make_project()
    with pytest.raises(KeyError):
        LoadRegistry.remove(project, "nonexistent-id")


def test_set_active_toggle():
    project = _make_project()
    series = _make_series()
    LoadRegistry.add(project, series)
    assert project.load_series[0].is_active is True

    LoadRegistry.set_active(project, series.id, False)
    assert project.load_series[0].is_active is False

    LoadRegistry.set_active(project, series.id, True)
    assert project.load_series[0].is_active is True


def test_set_active_nonexistent_raises():
    project = _make_project()
    with pytest.raises(KeyError):
        LoadRegistry.set_active(project, "bad-id", True)


def test_recompute_bess_with_no_bess_is_noop():
    project = _make_project()
    series = _make_series()
    LoadRegistry.add(project, series)
    # No BESS series — recompute_bess should not crash
    LoadRegistry.recompute_bess(project)
    assert len(project.load_series) == 1


def test_recompute_bess_updates_bess_values():
    project = _make_project()
    slp = _make_series(SeriesType.SLP, value=20.0)
    LoadRegistry.add(project, slp)

    bess_params = BESSParameters(
        capacity_kwh=100.0,
        max_charge_power_kw=30.0,
        max_discharge_power_kw=30.0,
        efficiency_pct=90.0,
        strategy=BESSStrategy.ARBITRAGE,
        peak_shaving_threshold_kw=None,
    )
    bess = LoadSeries(
        id=str(uuid.uuid4()),
        name="BESS",
        series_type=SeriesType.BESS,
        parameters=bess_params,
        values=np.zeros(35040).tolist(),
    )
    project.load_series.append(bess)
    LoadRegistry.recompute_bess(project)

    bess_vals = np.array(project.load_series[-1].values)
    assert bess_vals.shape == (35040,)
    assert not np.all(bess_vals == 0.0)


def test_update_parameters():
    project = _make_project()
    series = _make_series()
    LoadRegistry.add(project, series)

    new_params = SLPParameters(profile_type="G0", annual_energy_kwh=2000.0)

    import os
    import pandas as pd

    bdew_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "bdew"
    )
    bdew_profiles = {}
    for name in ["H0", "G0"]:
        path = os.path.join(bdew_dir, f"{name}.csv")
        if os.path.exists(path):
            bdew_profiles[name] = pd.read_csv(path)

    LoadRegistry.update(project, series.id, new_params, bdew_profiles=bdew_profiles)
    assert project.load_series[0].parameters.profile_type == "G0"
    assert project.load_series[0].parameters.annual_energy_kwh == 2000.0


def test_update_nonexistent_raises():
    project = _make_project()
    new_params = SLPParameters(profile_type="G0", annual_energy_kwh=2000.0)
    with pytest.raises(KeyError):
        LoadRegistry.update(project, "bad-id", new_params)
