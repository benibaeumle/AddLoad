"""Unit tests for ExportEngine."""

from __future__ import annotations

import json
import uuid

import numpy as np
import pytest

from src.aggregator import Aggregator
from src.export_engine import ExportEngine
from src.models.load_series import LoadSeries, SLPParameters
from src.models.project import SeriesType
from src.services.project_service import ProjectService


def _project_with_series():
    project = ProjectService.create(
        kunde="Test", ersteller="Dev", adresse="Teststr.", seed=0
    )
    vals = np.linspace(0, 10, 35040).tolist()
    params = SLPParameters(profile_type="H0", annual_energy_kwh=1000.0)
    series = LoadSeries(
        id=str(uuid.uuid4()),
        name="Test SLP",
        series_type=SeriesType.SLP,
        parameters=params,
        values=vals,
    )
    project.load_series.append(series)
    return project


def test_to_csv_bytes_returns_bytes():
    project = _project_with_series()
    result = Aggregator.compute(project)
    csv_bytes = ExportEngine.to_csv_bytes(result)
    assert isinstance(csv_bytes, bytes)


def test_to_csv_bytes_has_bom():
    project = _project_with_series()
    result = Aggregator.compute(project)
    csv_bytes = ExportEngine.to_csv_bytes(result)
    assert csv_bytes[:3] == b"\xef\xbb\xbf"


def test_to_csv_bytes_semicolon_delimiter():
    project = _project_with_series()
    result = Aggregator.compute(project)
    csv_bytes = ExportEngine.to_csv_bytes(result)
    header = csv_bytes.decode("utf-8-sig").splitlines()[0]
    assert ";" in header
    assert "," not in header


def test_to_csv_bytes_35040_rows():
    project = _project_with_series()
    result = Aggregator.compute(project)
    csv_bytes = ExportEngine.to_csv_bytes(result)
    lines = [l for l in csv_bytes.decode("utf-8-sig").splitlines() if l.strip()]
    assert len(lines) - 1 == 35040


def test_to_json_bytes_returns_valid_json():
    project = _project_with_series()
    json_bytes = ExportEngine.to_json_bytes(project)
    data = json.loads(json_bytes.decode("utf-8"))
    assert data["schema_version"] == "1.0"


def test_to_json_bytes_raises_on_invalid_project():
    project = ProjectService.create(kunde="", ersteller="", adresse="")
    with pytest.raises(ValueError):
        ExportEngine.to_json_bytes(project)
