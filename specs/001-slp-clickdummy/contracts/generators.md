# Contract: Generators

**Modules**: `src/generators/slp_generator.py`, `ps_builder.py`, `pv_generator.py`, `bess_simulator.py`  
**Date**: 2026-03-21

All generators are **pure functions** (no side effects, no global state). Each
accepts parameters + a time index and returns a `numpy.ndarray` of shape `(35040,)`
with dtype `float64` representing power in kW at each 15-minute UTC step.

---

## SLPGenerator

### `SLPGenerator.generate(params: SLPParameters, target_year: int, bdew_profiles: dict) -> np.ndarray`

Generates a scaled BDEW SLP time series.

**Algorithm**:
1. Build a 35040-element array by mapping each time step to `(saison, tagesart, slot_index)`.
2. Look up the normalised value from `bdew_profiles[params.profile_type]`.
3. Apply dynamisation factor `F(d)` for H0 profiles (see `research.md §1`).
4. Scale: `values = raw_values * (params.annual_energy_kwh / 1000.0)`.

**Preconditions**: `params.profile_type` ∈ {H0, G0, G1, G2, G3, G4, G5, G6, L0, L1, L2}; `params.annual_energy_kwh >= 0`  
**Postconditions**: `values.sum() * 0.25 ≈ params.annual_energy_kwh` (±0.1%); all values ≥ 0  
**Raises**: `KeyError` if `profile_type` not in `bdew_profiles`

---

## PSBuilder

### `PSBuilder.build(params: PSParameters, target_year: int, bdew_profiles: dict) -> np.ndarray`

Computes the aggregated Power Summary load curve via depth-first post-order traversal.

**Algorithm**:
1. For each CONSUMER leaf: call `SLPGenerator.generate` with the consumer's parameters.
2. For each GROUP node: sum child arrays element-wise, multiply by `simultaneity_factor`.
3. Return the root node's resulting array.

**Preconditions**: all CONSUMER nodes have valid `profile_type` and `annual_energy_kwh ≥ 0`; all GROUP `simultaneity_factor` values are in (0, 1]  
**Postconditions**: result shape is `(35040,)`; all values ≥ 0  
**Raises**: `ValueError` if a CONSUMER has `profile_type = None`; `ValueError` if any `simultaneity_factor` is 0 or negative

---

## PVGenerator

### `PVGenerator.generate(params: PVAParameters, target_year: int, seed: int) -> np.ndarray`

Generates a synthetic annual PV generation profile.

**Algorithm**: See `research.md §3`. Outputs negative kW (generation convention).

**Preconditions**: `params.peak_power_kwp >= 0`; `0 <= params.azimuth_deg <= 360`; `0 <= params.tilt_deg <= 90`  
**Postconditions**:
- All values ≤ 0 kW
- Night-time steps (astronomical darkness) = 0.0 exactly
- `abs(values).sum() * 0.25` ∈ [900, 1100] × `params.peak_power_kwp` for `climate_zone = "central_europe"`, azimuth=180°, tilt=30°
- Result is deterministic for fixed `(params, target_year, seed)`

**Raises**: `ValueError` if `peak_power_kwp < 0`

---

## BESSSimulator

### `BESSSimulator.simulate(params: BESSParameters, net_load: np.ndarray) -> np.ndarray`

Runs the discrete time-step BESS simulation.

**Inputs**:
- `params`: BESS configuration including strategy
- `net_load`: 35040-element array representing the net load curve **excluding** this BESS (kW, positive = consumption)

**Algorithm**: See `research.md §4`. Positive result = discharge (reduces net load); negative = charge.

**Preconditions**:
- `net_load.shape == (35040,)`
- `params.capacity_kwh > 0`
- `params.max_charge_power_kw > 0`, `params.max_discharge_power_kw > 0`
- `0 < params.efficiency_pct <= 100`

**Postconditions**:
- `|values[t]| <= max(max_charge_power_kw, max_discharge_power_kw)` for all `t`
- Simulated SOC is always in `[0, params.capacity_kwh]`
- For `PEAK_SHAVING`: `max(net_load + values) <= max(net_load)` (peak is not worsened)

**Raises**: `ValueError` if `net_load.shape != (35040,)` or any capacity/power parameter ≤ 0

---

## Shared Generator Conventions

| Convention | Value |
|---|---|
| Return type | `numpy.ndarray`, dtype `float64`, shape `(35040,)` |
| Power unit | kW |
| Time step | 15 min (0.25 h) |
| Load sign | Positive = consumption; negative = generation |
| Missing steps | 0.0 (never NaN) |
| Determinism | Same inputs → same output (seeded where stochastic) |
