"""Integration test: SC-002 — JSON project round-trip (save → load cycle)."""

from __future__ import annotations

from src.services.project_service import ProjectService


def test_project_roundtrip_empty():
    """A freshly created project serialises and deserialises without data loss."""
    project = ProjectService.create(
        kunde="Musterkunde GmbH",
        ersteller="Max Mustermann",
        adresse="Musterstraße 1, 12345 Musterstadt",
        seed=42,
    )

    json_str = ProjectService.to_json(project)
    loaded, skipped = ProjectService.from_json(json_str)

    assert skipped == []
    assert loaded.uuid == project.uuid
    assert loaded.kunde == project.kunde
    assert loaded.ersteller == project.ersteller
    assert loaded.adresse == project.adresse
    assert loaded.seed == project.seed
    assert loaded.target_year == project.target_year
    assert loaded.schema_version == project.schema_version
    assert len(loaded.load_series) == 0


def test_project_roundtrip_preserves_static_limits():
    """Static limits survive a JSON round-trip."""
    project = ProjectService.create(
        kunde="Test",
        ersteller="Dev",
        adresse="Teststr. 1",
        seed=1,
    )
    project.static_limits.sicherung_kw = 100.0
    project.static_limits.hausanschluss_kw = 250.0
    project.static_limits.trafo_kw = None

    json_str = ProjectService.to_json(project)
    loaded, _ = ProjectService.from_json(json_str)

    assert loaded.static_limits.sicherung_kw == 100.0
    assert loaded.static_limits.hausanschluss_kw == 250.0
    assert loaded.static_limits.trafo_kw is None


def test_project_roundtrip_with_slp_series(bdew_profiles):
    """A project with one SLP series round-trips without data loss."""
    import numpy as np

    from src.generators.slp_generator import SLPGenerator
    from src.models.load_series import LoadSeries, SLPParameters
    from src.models.project import SeriesType
    from src.services.load_registry import LoadRegistry
    import uuid

    project = ProjectService.create(
        kunde="Test",
        ersteller="Dev",
        adresse="Teststr.",
        seed=0,
    )
    params = SLPParameters(profile_type="H0", annual_energy_kwh=5000.0)
    values = SLPGenerator.generate(params, project.target_year, bdew_profiles)
    series = LoadSeries(
        id=str(uuid.uuid4()),
        name="H0 5000",
        series_type=SeriesType.SLP,
        parameters=params,
        values=values.tolist(),
    )
    LoadRegistry.add(project, series)

    json_str = ProjectService.to_json(project)
    loaded, skipped = ProjectService.from_json(json_str)

    assert skipped == []
    assert len(loaded.load_series) == 1
    s = loaded.load_series[0]
    assert s.series_type == SeriesType.SLP
    assert s.parameters.profile_type == "H0"
    assert abs(s.parameters.annual_energy_kwh - 5000.0) < 1e-6
    np.testing.assert_allclose(
        np.array(s.values), np.array(series.values), rtol=1e-5
    )


import pytest
import os
import pandas as pd


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
