"""Unit tests for Normalizer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.normalizer import Normalizer
from src.models.load_series import MergeMode


def test_canonical_index_length():
    idx = Normalizer.canonical_index(2024)
    assert len(idx) == 35040


def test_canonical_index_no_feb29():
    idx = Normalizer.canonical_index(2024)
    feb29 = idx[(idx.month == 2) & (idx.day == 29)]
    assert len(feb29) == 0


def test_canonical_index_non_leap_year():
    idx = Normalizer.canonical_index(2023)
    assert len(idx) == 35040


def test_canonical_index_utc():
    idx = Normalizer.canonical_index(2024)
    assert str(idx.tz) == "UTC"


def test_align_basic():
    idx = pd.date_range("2023-01-01", periods=35040, freq="15min", tz="UTC")
    s = pd.Series(np.ones(35040), index=idx)
    result = Normalizer.align(s, 2023)
    assert result.shape == (35040,)
    assert np.all(result == 1.0)


def test_align_fills_nan_with_zero():
    idx = pd.date_range("2023-01-01", periods=35040, freq="15min", tz="UTC")
    data = np.ones(35040)
    data[100] = np.nan
    s = pd.Series(data, index=idx)
    result = Normalizer.align(s, 2023)
    assert result[100] == 0.0


def test_align_partial_year_pads_with_zeros():
    idx = pd.date_range("2024-01-01", periods=100, freq="15min", tz="UTC")
    s = pd.Series(np.ones(100), index=idx)
    result = Normalizer.align(s, 2024)
    assert result.shape == (35040,)
    assert np.all(result[:100] == 1.0)
    assert np.all(result[100:] == 0.0)


def test_merge_individual_passthrough():
    arrays = [np.ones(35040), np.ones(35040) * 2]
    result = Normalizer.merge_series(arrays, MergeMode.INDIVIDUAL)
    assert isinstance(result, list)
    assert len(result) == 2


def test_merge_combined_sums():
    arrays = [np.ones(35040), np.ones(35040) * 2]
    result = Normalizer.merge_series(arrays, MergeMode.COMBINED)
    assert result.shape == (35040,)
    assert np.all(result == 3.0)


def test_merge_wrong_shape_raises():
    arrays = [np.ones(35040), np.ones(100)]
    with pytest.raises(ValueError):
        Normalizer.merge_series(arrays, MergeMode.COMBINED)
