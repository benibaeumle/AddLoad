"""BESSSimulator: discrete time-step battery energy storage simulation."""

from __future__ import annotations

import math

import numpy as np

from src.models.load_series import BESSParameters, BESSStrategy


class BESSSimulator:
    """Runs a forward-pass discrete BESS simulation over 35040 time steps."""

    @staticmethod
    def simulate(params: BESSParameters, net_load: np.ndarray) -> np.ndarray:
        """Simulate the BESS dispatch over the net load curve.

        Uses symmetric round-trip efficiency split:
        - Charging: eta_charge = sqrt(eta)
        - Discharging: eta_discharge = sqrt(eta)

        Args:
            params: BESSParameters with capacity, power limits, efficiency, strategy.
            net_load: 35040-element array of net load (kW), positive = consumption.

        Returns:
            numpy array of shape (35040,) with BESS dispatch values (kW).
            The result is added to net load: positive = charge, negative = discharge.

        Raises:
            ValueError: if net_load has wrong shape or any capacity/power param <= 0.
        """
        if net_load.shape != (35040,):
            raise ValueError(
                f"net_load muss die Form (35040,) haben, erhalten: {net_load.shape}"
            )
        if params.capacity_kwh <= 0:
            raise ValueError("capacity_kwh muss > 0 sein.")
        if params.max_charge_power_kw <= 0:
            raise ValueError("max_charge_power_kw muss > 0 sein.")
        if params.max_discharge_power_kw <= 0:
            raise ValueError("max_discharge_power_kw muss > 0 sein.")
        if not (0 < params.efficiency_pct <= 100):
            raise ValueError("efficiency_pct muss im Bereich (0, 100] liegen.")

        if net_load.sum() == 0:
            import warnings
            warnings.warn(
                "net_load enthält nur Nullen. Das BESS-Profil wird ebenfalls null sein.",
                stacklevel=2,
            )

        eta = params.efficiency_pct / 100.0
        eta_charge = math.sqrt(eta)
        eta_discharge = math.sqrt(eta)

        capacity = params.capacity_kwh
        max_charge = params.max_charge_power_kw
        max_discharge = params.max_discharge_power_kw
        dt = 0.25

        threshold = params.peak_shaving_threshold_kw
        if threshold is None and params.strategy == BESSStrategy.PEAK_SHAVING:
            threshold = float(np.percentile(net_load, 90))
        if params.strategy == BESSStrategy.PEAK_SHAVING:
            threshold = min(float(threshold), float(np.max(net_load)))

        result = np.zeros(35040, dtype=float)
        soc = 0.0

        for t in range(35040):
            p_net = net_load[t]

            if params.strategy == BESSStrategy.PEAK_SHAVING:
                target = _dispatch_peak_shaving(
                    p_net, max_charge, max_discharge, threshold
                )
            elif params.strategy == BESSStrategy.EIGENVERBRAUCH:
                target = _dispatch_eigenverbrauch(
                    p_net, max_charge, max_discharge
                )
            elif params.strategy == BESSStrategy.ARBITRAGE:
                hour = (t // 4) % 24
                target = _dispatch_arbitrage(max_charge, max_discharge, hour)
            else:
                target = 0.0

            actual = float(np.clip(target, -max_discharge, max_charge))

            # Dispatch is additive to net load: charge is positive, discharge negative.
            if actual < 0:
                discharge_power = min(-actual, soc * eta_discharge / dt)
                new_soc = soc - discharge_power * dt / eta_discharge
                actual = -discharge_power
            else:
                charge_power = min(
                    actual, (capacity - soc) / (dt * eta_charge)
                )
                new_soc = soc + charge_power * dt * eta_charge
                actual = charge_power

            soc = float(np.clip(new_soc, 0.0, capacity))
            result[t] = actual

        return result


def _dispatch_peak_shaving(
    p_net: float,
    max_charge: float,
    max_discharge: float,
    threshold: float,
) -> float:
    """Keep resulting net load at or below the peak-shaving threshold."""
    if p_net > threshold:
        return -min(p_net - threshold, max_discharge)
    if p_net < threshold:
        return min(threshold - p_net, max_charge)
    return 0.0



def _dispatch_eigenverbrauch(
    p_net: float,
    max_charge: float,
    max_discharge: float,
) -> float:
    """Eigenverbrauch: charge on PV surplus, discharge to cover remaining load."""
    if p_net < 0:
        return min(abs(p_net), max_charge)
    if p_net > 0:
        return -min(p_net, max_discharge)
    return 0.0


def _dispatch_arbitrage(
    max_charge: float,
    max_discharge: float,
    hour: int,
) -> float:
    """Arbitrage: charge 00:00-06:00, discharge 17:00-21:00."""
    if 0 <= hour < 6:
        return max_charge
    if 17 <= hour < 21:
        return -max_discharge
    return 0.0
