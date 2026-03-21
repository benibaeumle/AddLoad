"""PVGenerator: synthetic annual PV generation profile."""

from __future__ import annotations

import math

import numpy as np

from src.models.load_series import PVAParameters
from src.normalizer import Normalizer

_LAT_DEG = 51.0
_LAT_RAD = math.radians(_LAT_DEG)


class PVGenerator:
    """Generates a synthetic seed-reproducible PV generation time series."""

    @staticmethod
    def generate(
        params: PVAParameters,
        target_year: int,
        seed: int,
    ) -> np.ndarray:
        """Generate a 35040-element PV generation array (all values <= 0).

        Uses a trigonometric solar model (declination, hour angle, zenith angle,
        tilt/azimuth transposition) with a seasonal clearsky envelope and
        seed-deterministic cloud-cover variation.

        Args:
            params: PVAParameters with peak_power_kwp, azimuth_deg, tilt_deg,
                    and climate_zone.
            target_year: The target year for the time grid.
            seed: Integer seed for numpy random cloud-cover variation.

        Returns:
            numpy array of shape (35040,), dtype float64, all values <= 0.

        Raises:
            ValueError: if peak_power_kwp < 0.
        """
        if params.peak_power_kwp < 0:
            raise ValueError(
                f"peak_power_kwp muss >= 0 sein, erhalten: {params.peak_power_kwp}"
            )

        canonical = Normalizer.canonical_index(target_year)
        n = len(canonical)
        values = np.zeros(n, dtype=float)

        azimuth_rad = math.radians(params.azimuth_deg)
        tilt_rad = math.radians(params.tilt_deg)

        rng = np.random.default_rng(seed)
        n_days = 365
        cloud_daily = rng.normal(loc=1.0, scale=0.15, size=n_days)
        cloud_daily = np.clip(cloud_daily, 0.0, 1.5)

        for i, ts in enumerate(canonical):
            doy = ts.day_of_year
            hour_utc = ts.hour + ts.minute / 60.0

            decl_rad = math.radians(23.45 * math.sin(math.radians(360.0 / 365.0 * (doy - 81))))
            hour_angle_rad = math.radians(15.0 * (hour_utc - 12.0))

            cos_zenith = (
                math.sin(_LAT_RAD) * math.sin(decl_rad)
                + math.cos(_LAT_RAD) * math.cos(decl_rad) * math.cos(hour_angle_rad)
            )
            cos_zenith = max(0.0, cos_zenith)

            if cos_zenith <= 0.0:
                values[i] = 0.0
                continue

            sin_zenith = math.sqrt(max(0.0, 1.0 - cos_zenith**2))
            azimuth_sun = math.atan2(
                math.sin(hour_angle_rad),
                math.cos(hour_angle_rad) * math.sin(_LAT_RAD)
                - math.tan(decl_rad) * math.cos(_LAT_RAD),
            )

            cos_aoi = (
                math.sin(decl_rad) * math.sin(_LAT_RAD) * math.cos(tilt_rad)
                - math.sin(decl_rad) * math.cos(_LAT_RAD) * math.sin(tilt_rad) * math.cos(azimuth_rad)
                + math.cos(decl_rad) * math.cos(_LAT_RAD) * math.cos(tilt_rad) * math.cos(hour_angle_rad)
                + math.cos(decl_rad) * math.sin(_LAT_RAD) * math.sin(tilt_rad) * math.cos(azimuth_rad) * math.cos(hour_angle_rad)
                + math.cos(decl_rad) * math.sin(tilt_rad) * math.sin(azimuth_rad) * math.sin(hour_angle_rad)
            )
            cos_aoi = max(0.0, cos_aoi)

            clearsky = 0.75 + 0.25 * math.sin(math.radians(360.0 / 365.0 * (doy - 80)))

            day_idx = min(doy - 1, n_days - 1)
            cloud_factor = cloud_daily[day_idx]

            power = params.peak_power_kwp * cos_aoi * clearsky * cloud_factor
            values[i] = -max(0.0, power)

        target_yield_ratio = 0.95
        if params.peak_power_kwp > 0:
            current_yield = abs(values.sum()) * 0.25
            expected_yield = params.peak_power_kwp * 950.0
            if current_yield > 0:
                scale = expected_yield / current_yield
                values = values * scale

        return values
