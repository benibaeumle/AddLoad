"""SLPGenerator: generates scaled BDEW standard load profile time series."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.models.load_series import SLPParameters
from src.normalizer import Normalizer

# BDEW season boundaries (month, day)
_WINTER_END = (3, 20)      # Winter ends Mar 20
_SOMMER_START = (5, 15)    # Sommer starts May 15
_SOMMER_END = (9, 14)      # Sommer ends Sep 14
_WINTER_START = (11, 1)    # Winter starts Nov 1


def _get_season(month: int, day: int) -> str:
    """Return the BDEW season for a given month and day."""
    if (month, day) <= _WINTER_END:
        return "winter"
    if (month, day) < _SOMMER_START:
        return "uebergang"
    if (month, day) <= _SOMMER_END:
        return "sommer"
    if (month, day) < _WINTER_START:
        return "uebergang"
    return "winter"


def _get_day_type(ts: pd.Timestamp) -> str:
    """Return the BDEW Tagesart for a timestamp (weekday/saturday/sunday)."""
    dow = ts.dayofweek  # 0=Mon … 6=Sun
    if dow == 5:
        return "samstag"
    if dow == 6:
        return "sonntag"
    return "werktag"


def _h0_dynamisation(day_of_year: int) -> float:
    """Compute H0 dynamisation factor F(d) for day d (1-based)."""
    d = day_of_year
    return (
        -3.92e-10 * d**4
        + 3.20e-7 * d**3
        - 7.02e-5 * d**2
        + 2.10e-3 * d
        + 1.24
    )


class SLPGenerator:
    """Generates a scaled BDEW SLP time series for a target year."""

    @staticmethod
    def generate(
        params: SLPParameters,
        target_year: int,
        bdew_profiles: dict,
    ) -> np.ndarray:
        """Generate a 35040-element power array from a BDEW SLP profile.

        Maps each 15-min step to (saison, tagesart, slot_index), looks up
        the normalised value, applies H0 dynamisation if needed, then scales
        by annual_energy_kwh / 1000.0.

        Args:
            params: SLPParameters with profile_type and annual_energy_kwh.
            target_year: The target year for the time grid.
            bdew_profiles: Dict mapping profile type strings to pd.DataFrames
                           with columns: saison, tagesart, slot_index,
                           value_kw_per_1000kwha.

        Returns:
            numpy array of shape (35040,), dtype float64, all values >= 0.

        Raises:
            KeyError: if profile_type not in bdew_profiles.
        """
        if params.profile_type not in bdew_profiles:
            raise KeyError(
                f"Profil '{params.profile_type}' nicht in den BDEW-Profilen gefunden."
            )

        profile_df = bdew_profiles[params.profile_type]

        lookup: dict[tuple, float] = {}
        for row in profile_df.itertuples(index=False):
            lookup[(row.saison, row.tagesart, int(row.slot_index))] = float(
                row.value_kw_per_1000kwha
            )

        canonical = Normalizer.canonical_index(target_year)
        values = np.empty(len(canonical), dtype=float)

        is_h0 = params.profile_type == "H0"

        for i, ts in enumerate(canonical):
            season = _get_season(ts.month, ts.day)
            day_type = _get_day_type(ts)
            slot_index = (ts.hour * 60 + ts.minute) // 15
            raw = lookup.get((season, day_type, slot_index), 0.0)

            if is_h0:
                doy = ts.day_of_year
                raw = raw * _h0_dynamisation(doy)

            values[i] = raw

        values = values * (params.annual_energy_kwh / 1000.0)
        values = np.clip(values, 0.0, None)

        total_energy = values.sum() * 0.25
        if total_energy > 0 and params.annual_energy_kwh > 0:
            values = values * (params.annual_energy_kwh / total_energy)

        return values
