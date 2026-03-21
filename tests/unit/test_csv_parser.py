"""Unit tests for csv_parser."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest

from src.generators.csv_parser import parse_upload
from src.models.load_series import MergeMode


def _make_csv_bytes(n_rows: int = 35040, year: int = 2023, sep: str = ";") -> bytes:
    """Generate a minimal valid CSV with timestamp and power columns."""
    lines = [f"timestamp{sep}P_kW"]
    idx = pd.date_range(f"{year}-01-01", periods=n_rows, freq="15min", tz="UTC")
    rng = np.random.default_rng(0)
    vals = rng.uniform(0, 50, n_rows)
    for ts, v in zip(idx, vals):
        lines.append(f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')}{sep}{v:.3f}")
    return "\n".join(lines).encode("utf-8")


def _make_csv_no_timestamp(n_rows: int = 35040) -> bytes:
    """CSV with only a power column and no timestamp."""
    lines = ["P_kW"]
    rng = np.random.default_rng(1)
    vals = rng.uniform(0, 50, n_rows)
    for v in vals:
        lines.append(f"{v:.3f}")
    return "\n".join(lines).encode("utf-8")


def test_parse_basic_csv():
    csv_bytes = _make_csv_bytes(year=2023)
    arr, params, detected_year = parse_upload(csv_bytes, "test.csv", 2023)
    assert arr.shape == (35040,)
    assert params.source_filenames == ["test.csv"]
    assert params.merge_mode == MergeMode.INDIVIDUAL
    assert params.column_name == "P_kW"
    assert detected_year == 2023


def test_parse_no_timestamp_csv():
    csv_bytes = _make_csv_no_timestamp()
    arr, params, detected_year = parse_upload(csv_bytes, "notimestamp.csv", 2023)
    assert arr.shape == (35040,)


def test_parse_semicolon_separator():
    csv_bytes = _make_csv_bytes(year=2023, sep=";")
    arr, params, detected_year = parse_upload(csv_bytes, "semi.csv", 2023)
    assert arr.shape == (35040,)


def test_parse_comma_separator():
    csv_bytes = _make_csv_bytes(year=2023, sep=",")
    arr, params, detected_year = parse_upload(csv_bytes, "comma.csv", 2023)
    assert arr.shape == (35040,)


def test_parse_result_no_nan():
    csv_bytes = _make_csv_bytes(year=2023)
    arr, params, detected_year = parse_upload(csv_bytes, "test.csv", 2023)
    assert not np.any(np.isnan(arr))


def test_parse_partial_year_pads_with_zeros():
    lines = ["timestamp;P_kW"]
    idx = pd.date_range("2023-01-01", periods=100, freq="15min", tz="UTC")
    for ts in idx:
        lines.append(f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')};1.0")
    csv_bytes = "\n".join(lines).encode("utf-8")
    arr, params, detected_year = parse_upload(csv_bytes, "short.csv", 2023)
    assert arr.shape == (35040,)
    assert detected_year == 2023


def test_parse_xlsx(tmp_path):
    """Parse a simple XLSX file with a power column."""
    idx = pd.date_range("2023-01-01", periods=35040, freq="15min", tz="UTC")
    rng = np.random.default_rng(2)
    df = pd.DataFrame({
        "timestamp": idx.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "P_kW": rng.uniform(0, 50, 35040),
    })
    xlsx_path = tmp_path / "test.xlsx"
    df.to_excel(str(xlsx_path), index=False)
    xlsx_bytes = xlsx_path.read_bytes()
    arr, params, detected_year = parse_upload(xlsx_bytes, "test.xlsx", 2023)
    assert arr.shape == (35040,)
    assert params.source_filenames == ["test.xlsx"]
    assert detected_year == 2023
