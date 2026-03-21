"""Normalizer: canonical 15-minute UTC time grid and series alignment."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.load_series import MergeMode


class Normalizer:
    """Aligns time series onto the canonical 35040-step 15-min UTC grid."""

    @staticmethod
    def canonical_index(target_year: int) -> pd.DatetimeIndex:
        """Return the canonical 35040-step DatetimeIndex for the given year.

        Leap-year Feb 29 entries are excluded so the index always has exactly
        35040 entries.
        """
        idx = pd.date_range(
            start=f"{target_year}-01-01 00:00:00",
            end=f"{target_year}-12-31 23:45:00",
            freq="15min",
            tz="UTC",
        )
        idx = idx[~((idx.month == 2) & (idx.day == 29))]
        return idx

    @staticmethod
    def align(series: pd.Series, target_year: int) -> np.ndarray:
        """Align a pd.Series with a DatetimeIndex onto the canonical grid.

        Steps:
        1. Ensure UTC timezone.
        2. Resample to 15-min if needed (mean aggregation).
        3. Reindex to canonical_index.
        4. Fill NaN with 0.0.

        Raises:
            ValueError: if the series has fewer than 35040 non-null values
                after resampling (resolution mismatch).
        """
        s = series.copy()

        if s.index.tz is None:
            s.index = s.index.tz_localize("UTC")
        else:
            s.index = s.index.tz_convert("UTC")

        current_freq = pd.infer_freq(s.index)
        if current_freq != "15min" and current_freq != "15T":
            s = s.resample("15min").mean()

        canonical = Normalizer.canonical_index(target_year)
        s = s.reindex(canonical)
        s = s.fillna(0.0)
        return s.to_numpy(dtype=float)

    @staticmethod
    def merge_series(arrays: list[np.ndarray], mode: MergeMode) -> list[np.ndarray] | np.ndarray:
        """Combine multiple aligned arrays according to the merge mode.

        Args:
            arrays: List of numpy arrays each with shape (35040,).
            mode: INDIVIDUAL returns the list unchanged; COMBINED returns
                  element-wise sum.

        Raises:
            ValueError: if any array has wrong shape.
        """
        for i, arr in enumerate(arrays):
            if arr.shape != (35040,):
                raise ValueError(
                    f"Array {i} hat die falsche Form {arr.shape}. "
                    f"Erwartet wird (35040,)."
                )

        if mode == MergeMode.INDIVIDUAL:
            return arrays
        else:
            return np.sum(arrays, axis=0)
