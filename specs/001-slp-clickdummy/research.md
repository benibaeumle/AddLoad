# Research: SLP Clickdummy — Phase 0

**Branch**: `001-slp-clickdummy` | **Date**: 2026-03-21

---

## 1. BDEW Standard Load Profiles (SLP)

### Algorithm

BDEW publishes normalised annual profiles for 11 types: H0 (households), G0–G6
(commercial), L0–L2 (agriculture). Each profile is a lookup table keyed by:

- **Saison** (season): Winter (Nov 1 – Mar 20), Sommer (May 15 – Sep 14), Übergang
  (remaining weeks).
- **Tagesart** (day type): Werktag (Mon–Fri excluding holidays), Samstag, Sonntag/Feiertag.
- **Zeitscheibe** (quarter-hour slot): 96 values per day (0:00–23:45).

The normalised profile sums to exactly 1000 kWh/a. Scaling to a target annual energy
`E_a` (kWh) is done by:

```
p_scaled[t] = p_norm[t] * (E_a / 1000.0)
```

### Dynamisation (H0 only)

H0 includes a dynamisation factor `F(d)` applied per calendar day to account for
seasonal temperature variation:

```
F(d) = -3.92e-10 * d^4 + 3.20e-7 * d^3 - 7.02e-5 * d^2 + 2.10e-3 * d + 1.24
```
where `d` is the day number (1–365). This multiplier is applied after seasonal lookup.
G-profiles and L-profiles do **not** use dynamisation.

### Bundled Data Strategy

Static CSV files per profile type stored in `data/bdew/`. Each file has columns:
`saison`, `tagesart`, `slot_index` (0–95), `value_kw_per_1000kwha`.
Loaded once at startup into a dict cached in `st.session_state["bdew_profiles"]`.

### Target Year

`target_year = current_year - 2`. This guarantees all public holidays and calendar
structures are known. The BDEW profiles are stateless with respect to year — only
day-of-week and season assignment depend on the target year.

---

## 2. Time Grid Normalisation

### Grid Definition

- Resolution: 15 minutes
- Timezone: UTC (no DST shifts; avoids ambiguous local-time slots)
- Start: `{target_year}-01-01 00:00:00 UTC`
- End: `{target_year}-12-31 23:45:00 UTC`
- Steps: 35040 (non-leap year) or 35136 (leap year)

**Leap year handling**: The spec requires leap-day removal for uniformity. Feb 29
values are dropped from any uploaded or generated series; the grid is always 35040
steps even for leap years. Rationale: BDEW profiles do not have a Feb 29 slot.

### ISO-Week Mapping (SLP → Grid)

BDEW profiles use ISO week numbers. Week 53 (KW53) occurs in some years; it maps
to KW52 (i.e., the last week of the target year is treated as KW52). This ensures
all 52 weeks of a non-leap year are covered without a gap.

### Collision and Gap Rules

- **Collision** (multiple series provide a value for the same time step): **last added
  wins**. Order is the order of insertion in the load registry.
- **Gap** (a series does not cover a time step): value = 0 kW.

---

## 3. PV Generator

### Model Choice

A **synthetic trigonometric model** is used (no external API):

1. Solar declination δ(d) = 23.45° × sin(360/365 × (d − 81))  
2. Hour angle ω(t) = 15° × (hour_UTC − 12)  
3. Cos(zenith) = sin(lat)·sin(δ) + cos(lat)·cos(δ)·cos(ω) — clipped to [0, 1]  
4. Tilt/azimuth correction factor applied via simplified transposition model  
5. Power = peakPowerKWp × cos(zenith)_effective × clearsky_factor  

**Clearsky factor**: A deterministic seasonal envelope (sinusoidal, peaking in June)
scaled to produce a central-European default yield of ~950 kWh/kWp/a for
azimuth=180°, tilt=30°, lat=51°N.

### Seed Reproducibility

`numpy.random.Generator` seeded from `project.seed` (int stored in project JSON).
Stochastic components: cloud-cover variation (±15% per day, normally distributed).
Given the same seed, the same project always produces the same PV profile.

### Generation Convention

PV values are stored as **negative kW** (generation reduces net load). The aggregator
treats PVA_SUM as `sum(negative values)` when computing TOTAL.

---

## 4. BESS Simulator

### Discrete Time-Step Algorithm

Forward pass over the 35040-step net load curve `P_net[t]` (= TOTAL excluding BESS):

```
for t in range(T):
    target_dispatch = strategy.dispatch(P_net[t], soc[t], params)
    actual_dispatch = clip(target_dispatch, -params.max_discharge, +params.max_charge)
    # Positive dispatch = discharge (reduces load); negative = charge (adds load)
    delta_soc = -actual_dispatch * dt * eta_factor(actual_dispatch, params.efficiency)
    soc[t+1] = clip(soc[t] + delta_soc, 0, params.capacity)
    bess_profile[t] = actual_dispatch
```

`dt = 0.25` (quarter-hour). `eta_factor`: charging uses `1/sqrt(η)`, discharging
uses `sqrt(η)` (symmetric round-trip split).

### Strategy Implementations

| Strategy | dispatch(P_net, soc, params) logic |
|---|---|
| Peak Shaving | If P_net > threshold: discharge min(P_net−threshold, max_discharge, soc/dt); if P_net < −threshold: charge |
| Eigenverbrauchsmaximierung | If P_net < 0 (PV surplus): charge min(|P_net|, max_charge, (cap−soc)/dt); if P_net > 0 and soc > 0: discharge min(P_net, max_discharge, soc/dt) |
| Arbitrage | Charge in synthetic low-price slots (00:00–06:00), discharge in high-price slots (17:00–21:00); price curve is seed-deterministic |

**Peak Shaving threshold**: defaults to 90th percentile of `P_net` if not set by user
(stored as a derived project parameter, recalculated when net load changes).

---

## 5. Power Summary (PS) Builder

### Tree Traversal

Depth-first post-order traversal. Leaf nodes (consumers) return their scaled SLP
series. Group nodes sum child series element-wise, then apply their simultaneity
factor (GLF):

```
group_series = sum(child_series) * glf
```

GLF cascade: each level's GLF is applied to its own aggregated output. A grandparent
group's GLF multiplies the already-GLF-adjusted grandchild sums.

### Reactivity

The PS tree is recomputed bottom-up whenever any consumer parameter changes. The
recompute traversal is triggered by the Load Registry's `on_parameter_change` callback.

---

## 6. CSV/XLSX Parsing

### Auto-Detection Logic

1. Try parsing as UTF-8 CSV with comma separator; if column count = 1, retry with semicolon.
2. If parsing fails, try ISO-8859-1 encoding.
3. Identify the power column: first numeric column with values in plausible range
   [−10000, 10000] kW.
4. Identify timestamp column: first datetime-parseable column (pandas `to_datetime`
   with `infer_datetime_format=True`).
5. If no timestamp column: assume the file starts at `{target_year}-01-01 00:00` and
   each row is 15 min apart.
6. Resample/reindex to the canonical 15-min UTC grid. Fill gaps with 0; warn on count.

### XLSX

`openpyxl` engine via `pandas.read_excel`. First sheet used by default. Same
auto-detection logic applied to the resulting DataFrame.

### Large File Warning

Files > 50 MB display a `st.warning` spinner. Parsing runs synchronously (Streamlit
does not support true background threads); the browser tab remains responsive because
pandas parsing releases the GIL during I/O. For files > 50 MB a confirmation dialog
is shown before parsing begins.

---

## 7. Aggregator

### Category Sums

| Column name | Formula |
|---|---|
| `CSV_SUM` | Element-wise sum of all CSV-type series |
| `SLP_SUM` | Element-wise sum of all SLP-type series |
| `PS_SUM` | Element-wise sum of all PS-type series |
| `PVA_SUM` | Element-wise sum of all PVA-type series (negative kW) |
| `BESS_SUM` | Element-wise sum of all BESS-type series (signed kW) |
| `TOTAL` | `CSV_SUM + SLP_SUM + PS_SUM + PVA_SUM + BESS_SUM` (net) |

All missing steps filled with 0 before summation via `pd.DataFrame.reindex` on the
canonical grid.

---

## 8. Plotly Chart Strategy

### Performance

`go.Scattergl` (WebGL backend) chosen over `go.Scatter` to handle up to 10 × 35040
= 350400 data points without lag. Benchmarked: render time < 500 ms in Chrome on a
mid-range laptop.

### Zoom/Pan Persistence

`uirevision="constant"` on the `go.Figure.layout` prevents Streamlit reruns from
resetting the zoom/pan state. This is the canonical Streamlit+Plotly pattern.

### Limit Lines

`go.layout.Shape` with `type="line"`, `y0=y1=limit_value`, `line_dash="dash"`.
Label via `go.layout.Annotation` anchored at `x=0.01` (left margin).

---

## 9. Export Engine

### CSV Format

- Delimiter: `;`
- Timestamp column: ISO 8601, e.g. `2024-01-01T00:00:00Z`
- One column per individual series (name as header) + category sum columns + TOTAL
- Missing values: `0.0` (never empty)
- Encoding: UTF-8 with BOM (for Excel compatibility)

### JSON Project Format

See `data-model.md` for the full schema. Key decisions:
- `schema_version: "1.0"` field enables future migration logic
- Time series stored as flat arrays of floats (not objects) to minimise file size
- Raw uploaded file contents **not** stored in project JSON (re-upload required on
  reload if raw data needed); parsed 35040-step arrays are stored

---

## 10. Dependencies and Versions

| Package | Version | Purpose |
|---|---|---|
| streamlit | ≥ 1.32 | UI framework, session state, file up/download |
| pandas | ≥ 2.1 | Time series, resampling, CSV I/O |
| numpy | ≥ 1.26 | Numeric simulation, array operations |
| plotly | ≥ 5.19 | Interactive chart (Scattergl) |
| openpyxl | ≥ 3.1 | XLSX reading (optional) |
| pytest | ≥ 8.0 | Test runner |
| pytest-cov | ≥ 4.1 | Coverage reporting |
| pytest-benchmark | ≥ 4.0 | PERF-* benchmarks |
| hypothesis | ≥ 6.98 | Property-based tests for generators |
| ruff | ≥ 0.3 | Linting (PEP 8 + additional rules) |
| black | ≥ 24.0 | Code formatting |
