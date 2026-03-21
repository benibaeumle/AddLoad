"""Integration test: SC-005 — CSV export has correct headers, rows, no empty cells."""

from __future__ import annotations

import io
import os

import numpy as np
import pandas as pd
import pytest

from src.aggregator import Aggregator
from src.export_engine import ExportEngine
from src.generators.slp_generator import SLPGenerator
from src.models.load_series import LoadSeries, SLPParameters
from src.models.project import SeriesType
from src.services.load_registry import LoadRegistry
from src.services.project_service import ProjectService
import uuid


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
def project_with_slp(bdew_profiles):
    """Project with one H0 SLP series."""
    project = ProjectService.create(
        kunde="Test", ersteller="Dev", adresse="Teststr.", seed=0
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
    return project


def test_csv_export_row_count(project_with_slp):
    """CSV export must have exactly 35040 data rows."""
    result = Aggregator.compute(project_with_slp)
    csv_bytes = ExportEngine.to_csv_bytes(result)

    content = csv_bytes.decode("utf-8-sig")
    lines = [l for l in content.splitlines() if l.strip()]
    data_rows = lines[1:]
    assert len(data_rows) == 35040, f"Expected 35040 rows, got {len(data_rows)}"


def test_csv_export_no_empty_cells(project_with_slp):
    """CSV export must not contain empty cells."""
    result = Aggregator.compute(project_with_slp)
    csv_bytes = ExportEngine.to_csv_bytes(result)

    content = csv_bytes.decode("utf-8-sig")
    lines = [l for l in content.splitlines() if l.strip()]
    for i, line in enumerate(lines[1:], start=2):
        cells = line.split(";")
        for j, cell in enumerate(cells):
            assert cell.strip() != "", (
                f"Empty cell at row {i}, col {j}: '{line}'"
            )


def test_csv_export_has_total_column(project_with_slp):
    """CSV export must include TOTAL column."""
    result = Aggregator.compute(project_with_slp)
    csv_bytes = ExportEngine.to_csv_bytes(result)

    content = csv_bytes.decode("utf-8-sig")
    header = content.splitlines()[0]
    assert "TOTAL" in header


def test_csv_export_total_matches_aggregation(project_with_slp):
    """CSV TOTAL column sum must match aggregation result total sum (±1e-3)."""
    result = Aggregator.compute(project_with_slp)
    csv_bytes = ExportEngine.to_csv_bytes(result)

    content = csv_bytes.decode("utf-8-sig")
    lines = content.splitlines()
    headers = lines[0].split(";")
    total_idx = headers.index("TOTAL")

    csv_total = sum(
        float(l.split(";")[total_idx])
        for l in lines[1:]
        if l.strip()
    )
    assert abs(csv_total - result.total.sum()) < 1e-3
