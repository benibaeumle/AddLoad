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
        - Charging: eta_charge = 1 / sqrt(eta)
        - Discharging: eta_discharge = sqrt(eta)

        Args:
            params: BESSParameters with capacity, power limits, efficiency, strategy.
            net_load: 35040-element array of net load (kW), positive = consumption.

        Returns:
            numpy array of shape (35040,) with BESS dispatch values (kW).
            Positive = discharge (reduces net load); negative = charge.

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
        eta_charge = 1.0 / math.sqrt(eta)
        eta_discharge = math.sqrt(eta)

        capacity = params.capacity_kwh
        max_charge = params.max_charge_power_kw
        max_discharge = params.max_discharge_power_kw
        dt = 0.25

        threshold = params.peak_shaving_threshold_kw
        if threshold is None and params.strategy == BESSStrategy.PEAK_SHAVING:
            threshold = float(np.percentile(net_load, 90))

        seed_for_arbitrage: int | None = None

        result = np.zeros(35040, dtype=float)
        soc = 0.0

        for t in range(35040):
            p_net = net_load[t]

            if params.strategy == BESSStrategy.PEAK_SHAVING:
                target = _dispatch_peak_shaving(p_net, soc, capacity, max_charge, max_discharge, threshold, dt)
            elif params.strategy == BESSStrategy.EIGENVERBRAUCH:
                target = _dispatch_eigenverbrauch(p_net, soc, capacity, max_charge, max_discharge, dt)
            elif params.strategy == BESSStrategy.ARBITRAGE:
                hour = (t // 4) % 24
                target = _dispatch_arbitrage(p_net, soc, capacity, max_charge, max_discharge, hour, dt)
            else:
                target = 0.0

            actual = float(np.clip(target, -max_charge, max_discharge))

            if actual > 0:
                new_soc = float(np.clip(soc - actual * dt / eta_discharge, 0.0, capacity))
                actual = (soc - new_soc) * eta_discharge / dt
            else:
                new_soc = float(np.clip(soc - actual * dt * eta_charge, 0.0, capacity))
                actual = (soc - new_soc) / (eta_charge * dt) if eta_charge * dt > 0 else 0.0

            soc = new_soc
            result[t] = actual

        return result


def _dispatch_peak_shaving(
    p_net: float,
    soc: float,
    capacity: float,
    max_charge: float,
    max_discharge: float,
    threshold: float,
    dt: float,
) -> float:
    """Peak shaving dispatch: discharge when above threshold, charge when below."""
    if p_net > threshold:
        excess = p_net - threshold
        available = soc / dt if dt > 0 else 0.0
        return min(excess, max_discharge, available)
    else:
        space = (capacity - soc) / dt if dt > 0 else 0.0
        return -min(max_charge, space)



def _dispatch_eigenverbrauch(
    p_net: float,
    soc: float,
    capacity: float,
    max_charge: float,
    max_discharge: float,
    dt: float,
) -> float:
    """Eigenverbrauch: charge on PV surplus, discharge to cover remaining load."""
    if p_net < 0:
        surplus = abs(p_net)
        space = (capacity - soc) / dt if dt > 0 else 0.0
        return -min(surplus, max_charge, space)
    elif p_net > 0 and soc > 0:
        available = soc / dt if dt > 0 else 0.0
        return min(p_net, max_discharge, available)
    return 0.0


def _dispatch_arbitrage(
    p_net: float,
    soc: float,
    capacity: float,
    max_charge: float,
    max_discharge: float,
    hour: int,
    dt: float,
) -> float:
    """Arbitrage: charge 00:00-06:00, discharge 17:00-21:00."""
    if 0 <= hour < 6:
        space = (capacity - soc) / dt if dt > 0 else 0.0
        return -min(max_charge, space)
    elif 17 <= hour < 21:
        available = soc / dt if dt > 0 else 0.0
        return min(max_discharge, available)
    return 0.0
