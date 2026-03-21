# Feature Specification: SLP Clickdummy — Elektrische Lastgang-Verwaltung

**Feature Branch**: `001-slp-clickdummy`
**Created**: 2026-03-21
**Status**: Draft
**Input**: Browserbasierte MVP-Anwendung zur Erstellung, Verwaltung, Kombination, Visualisierung und zum Export elektrischer Lastgänge über ein Kalenderjahr.

## Assumptions

- The application runs entirely in the browser (client-side only); no server or authentication system is required.
- A "calendar year" comprises 8760 hourly time steps (or 35040 quarter-hourly steps); the resolution is assumed to be 15-minute intervals (35040 values) as per BDEW SLP convention, but treated as a configurable assumption.
- BDEW standard load profiles (H0, G0, G1–G6, L0, L1, L2) are bundled as static data within the application.
- PV generation profiles are computed from a simplified irradiance model (e.g., PVGIS-style lookup table or simplified sinusoidal model) based on peak power and orientation; external API calls are not required for MVP.
- BESS strategies (Peak Shaving, Eigenverbrauchsmaximierung, Arbitrage) are computed deterministically from the net load curve and BESS parameters; no real-time market data is needed.
- Uploaded CSV/XLSX files are expected to contain at least one column of numeric power values with an implied or explicit timestamp; parsing details are handled by best-effort auto-detection.
- Static limit values (Sicherung, Hausanschluss, Trafo) are entered manually per project by the user.
- "Missing values" in combined time series are treated as 0 kW.
- Export CSV uses semicolons as delimiter and ISO 8601 timestamps; project JSON export is a lossless round-trip format.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Projekt anlegen und Stammdaten pflegen (Priority: P1)

A planner opens the application, creates a new project, fills in the mandatory project metadata
(client name, creator name, address), and saves the project locally as a JSON file. Later they
reload the project from that file and continue working.

**Why this priority**: Without project management, no other feature is accessible. This is the
entry point for all other workflows and delivers immediate standalone value as a project registry.

**Independent Test**: Can be fully tested by creating a project, filling in metadata, exporting
the JSON, reloading it, and verifying that all metadata fields are correctly restored.

**Acceptance Scenarios**:

1. **Given** the application is open with no projects, **When** the user clicks "Neues Projekt erstellen", **Then** a new project is created with a generated UUID, empty metadata fields, and appears in the project list.
2. **Given** a project with all mandatory fields filled, **When** the user exports the project as JSON, **Then** a valid JSON file is downloaded containing the UUID, all metadata fields, and an empty load series list.
3. **Given** a previously exported project JSON file, **When** the user imports it, **Then** the project is restored with the correct UUID, metadata, and all load series data intact.
4. **Given** a project with missing mandatory fields (Kunde, Ersteller, or Adresse), **When** the user attempts to export, **Then** the application displays a clear validation message identifying the missing field(s) and blocks the export.
5. **Given** multiple projects exist, **When** the user selects a different project, **Then** the view switches to that project's data without affecting other projects.

---

### User Story 2 — Standardlastprofil (SLP / BDEW) hinzufügen (Priority: P2)

A planner adds one or more BDEW standard load profiles to a project by selecting a profile type
(e.g., H0, G0) and entering the annual energy demand in kWh. The application scales the normalized
profile to the given annual energy and adds it to the project's load series list.

**Why this priority**: SLP profiles are the most common input type for load estimation and
represent the simplest path from "no data" to a usable annual load curve.

**Independent Test**: Can be fully tested by adding an H0 profile with 5000 kWh/a and verifying
that the resulting time series sums to 5000 kWh when integrated over the year.

**Acceptance Scenarios**:

1. **Given** an open project, **When** the user selects profile type "H0" and enters 5000 kWh annual demand, **Then** a new load series appears in the project labeled "SLP H0 – 5000 kWh/a".
2. **Given** a newly created SLP load series, **When** the time series is inspected, **Then** it contains exactly one value per time step for the full calendar year and the sum equals the entered annual energy demand (±0.1%).
3. **Given** an existing SLP load series, **When** the user edits the annual energy value, **Then** the time series is recalculated proportionally and the sum matches the new value.
4. **Given** any project, **When** the user adds multiple SLP load series of different profile types, **Then** each appears as a separate named entry in the load series list.

---

### User Story 3 — Messdaten-Upload (CSV/XLSX) (Priority: P3)

A planner uploads one or more CSV or XLSX files containing measured power data. The application
parses the files, maps the columns to a time series, and creates a named load series for each
file (or a combined series if the user opts to merge multiple uploads).

**Why this priority**: Measured data is the most accurate input but requires file handling and
parsing logic. It delivers high value for real-world projects and is independent of all profile
generation features.

**Independent Test**: Can be tested by uploading a known CSV file and verifying that the parsed
values match the source data and the series appears in the load list.

**Acceptance Scenarios**:

1. **Given** a valid CSV file with a power column (kW) at 15-minute resolution, **When** the user uploads it, **Then** a new load series is created with values matching the file contents (±0.01 kW per step).
2. **Given** an XLSX file with a single sheet and numeric power column, **When** uploaded, **Then** it is parsed and produces the same result as an equivalent CSV.
3. **Given** multiple uploaded files, **When** the user selects "gemeinsam verarbeiten" (merge), **Then** the values are summed element-wise and a single combined series is added.
4. **Given** a file with missing or non-numeric values in the power column, **When** uploaded, **Then** missing values are treated as 0 kW and the user is shown a warning with the count of replaced values.
5. **Given** a file whose number of rows does not match the expected annual resolution, **When** uploaded, **Then** the application shows a clear error message stating the mismatch and does not add a partial series.

---

### User Story 4 — Power Summary (PS) modellieren (Priority: P4)

A planner models a hierarchical consumption structure using Power Summary: they create groups,
sub-groups, and individual consumers. Each consumer receives a load profile type and an annual
energy demand. Simultaneity factors can be applied at group and sub-group level. The application
computes the aggregated annual load curve.

**Why this priority**: PS is the most powerful but most complex input type. It is independent of
SLP and CSV features and delivers unique value for structured modelling of multiple consumers.

**Independent Test**: Can be tested by creating a group with two consumers (each with a known
SLP + kWh/a), applying a simultaneity factor, and verifying the aggregated series equals
factor × (series1 + series2).

**Acceptance Scenarios**:

1. **Given** an open project, **When** the user creates a PS group with two consumers each using H0 at 3000 kWh/a, **Then** the PS load series equals the element-wise sum of both scaled H0 profiles.
2. **Given** a PS group with a simultaneity factor of 0.8 applied, **When** the aggregate is computed, **Then** every value in the resulting series equals 0.8 × (sum of consumer values at that time step).
3. **Given** a nested structure (group → sub-group → consumers), **When** a simultaneity factor is set at the sub-group level, **Then** only the sub-group's contribution is scaled; the parent group aggregation uses the already-scaled sub-group values.
4. **Given** a PS structure, **When** the user changes a consumer's annual energy demand, **Then** the PS aggregate series is immediately recalculated.
5. **Given** a PS load series, **When** viewed in the chart, **Then** it appears as a single aggregated curve labelled with the PS root group name.

---

### User Story 5 — Photovoltaikanlage (PVA) hinzufügen (Priority: P5)

A planner adds a PV system by entering peak power (kWp) and orientation parameters (azimuth,
tilt angle, and optionally location/climate zone). The application generates an annual generation
profile and adds it as a generation (negative load) series.

**Why this priority**: PV generation offsets load and is a common component in modern energy
planning. It is self-contained and independent of other load series types.

**Independent Test**: Can be tested by adding a 10 kWp south-facing PV system and verifying
that the resulting profile has zero generation at night, peak generation near solar noon in
summer, and a plausible annual yield (for a central-European location: ~900–1100 kWh/kWp/a).

**Acceptance Scenarios**:

1. **Given** a PV system with 10 kWp, azimuth 180° (south), tilt 30°, **When** added to the project, **Then** a generation series with non-positive values (≤ 0 kW convention for generation) is created for all time steps.
2. **Given** the PV series, **When** values at night (0:00–4:00 local time in winter) are inspected, **Then** all values are exactly 0 kW.
3. **Given** the PV series, **When** the annual sum of absolute generation is computed, **Then** it falls within a plausible range for the chosen parameters (assumption: 900–1100 kWh/kWp/a for central Europe).
4. **Given** an existing PV series, **When** the user changes the peak power, **Then** the series is recalculated proportionally.

---

### User Story 6 — Batteriespeichersystem (BESS) hinzufügen (Priority: P6)

A planner adds a battery storage system by entering capacity (kWh), charge/discharge power
(kW), round-trip efficiency (%), and selecting an operating strategy. The application computes
an annual storage power profile based on the net load curve (sum of all other series) and the
chosen strategy.

**Why this priority**: BESS is computationally dependent on other load series being present.
It is a high-value advanced feature that should be enabled only after foundational series types
are in place.

**Independent Test**: Can be tested by adding a BESS to a project that already has an SLP load
series and a PV series, selecting Peak Shaving, and verifying that the resulting BESS profile
respects the charge/discharge power and capacity constraints at every time step.

**Acceptance Scenarios**:

1. **Given** a project with a net load curve and a BESS (100 kWh, 50 kW charge/discharge, 90% efficiency, Peak Shaving), **When** the BESS profile is computed, **Then** charge and discharge power never exceed ±50 kW at any time step.
2. **Given** the BESS profile, **When** the simulated state of charge is tracked, **Then** it never exceeds 100 kWh or falls below 0 kWh at any time step.
3. **Given** Peak Shaving strategy, **When** computed, **Then** the combined curve (net load + BESS) has a lower peak than the net load curve alone.
4. **Given** Eigenverbrauchsmaximierung strategy, **When** a PV series is present, **Then** the BESS preferentially charges from PV surplus (PV > load) and discharges when PV is insufficient.
5. **Given** any BESS configuration, **When** the user changes the capacity or power parameter, **Then** the BESS profile is fully recomputed.

---

### User Story 7 — Jahresdarstellung und interaktives Chart (Priority: P2)

A planner views all active load series combined in a single interactive annual time series chart
(P in kW over time). They can toggle individual series on/off, view aggregated category sums
(SLP, CSV, PS, PVA, BESS, Gesamt), and see static limit lines (Sicherung, Hausanschluss,
Trafo). The chart supports panning and zooming.

**Why this priority**: The chart is the primary output of the application and is required from
the earliest usable state onward. It is co-equal with SLP addition in priority because seeing
the result is inseparable from adding the first load series.

**Independent Test**: Can be tested independently by adding at least one load series and
verifying that the chart renders, shows the correct series, responds to zoom/pan, and displays
limit lines at the correct kW values.

**Acceptance Scenarios**:

1. **Given** at least one load series in the project, **When** the chart view is opened, **Then** a P(t) time series chart renders with time on the x-axis (full calendar year) and power in kW on the y-axis.
2. **Given** multiple load series, **When** the user selects "Gesamt" (total), **Then** the chart shows the element-wise sum of all active series.
3. **Given** a mix of series types, **When** category aggregates are toggled, **Then** the chart correctly shows the sum per category (e.g., all SLP series summed as one curve).
4. **Given** static limit values set in the project, **When** the chart is displayed, **Then** horizontal dashed lines appear at the correct kW values, labelled with their names (Sicherung, Hausanschluss, Trafo).
5. **Given** the chart is rendered, **When** the user drags horizontally, **Then** the visible time window shifts (pan); when the user scrolls or pinches, the time axis zooms in/out.
6. **Given** the user toggles off a specific load series in the legend, **When** the chart updates, **Then** that series is hidden but all others remain visible and the total is recalculated without that series.

---

### User Story 8 — Daten exportieren (Priority: P3)

A planner exports the project in two formats: (a) a CSV file containing all individual load series
and aggregated series as columns, with timestamps in the first column; and (b) a JSON file
containing the full project definition including all parameters and load series data for
lossless round-trip import.

**Why this priority**: Export is required for handoff to clients and downstream tools. It is
independent of any specific load series type and can be tested as soon as at least one series
exists.

**Independent Test**: Can be tested by adding one SLP series and performing both exports.
The CSV must be parseable and contain the expected values; the JSON must be re-importable
without data loss.

**Acceptance Scenarios**:

1. **Given** a project with at least one load series, **When** the user triggers CSV export, **Then** a file is downloaded with a semicolon-delimited header row listing all series names and a timestamp column, followed by one data row per time step.
2. **Given** the exported CSV, **When** the total column values are summed, **Then** the result matches the in-app displayed total (±0.1%).
3. **Given** the exported CSV, **When** time steps with no data in a series are inspected, **Then** the value is 0 (not empty/null).
4. **Given** a project with all series types present, **When** the user triggers JSON project export, **Then** the downloaded JSON contains all load series parameters and time series data and can be re-imported to reproduce an identical project state.

---

### Edge Cases

- A project with zero load series: chart shows an empty canvas with limit lines only (if configured); exports produce headers-only CSV and valid empty JSON.
- Two load series with different time resolutions uploaded via CSV: the application resamples or rejects the mismatched file with a clear error.
- BESS added before any other series: net load curve is zero; BESS produces a zero profile; user is warned that BESS requires at least one other series.
- Annual energy demand entered as 0 kWh: the resulting SLP series is a zero curve; the user is warned but the series is still added.
- PV peak power of 0 kWp: produces a zero generation series; user is warned.
- Simultaneity factor of 0 or >1: values in range (0, 1] are accepted; 0 is rejected with validation error; values >1 are accepted with a warning (possible but unusual).
- JSON import with an unknown series type: unknown types are skipped with a warning; known types are restored normally.
- Very large CSV upload (>50 MB): application shows a progress indicator and must not freeze the browser tab.

---

## Requirements *(mandatory)*

### Functional Requirements

**Project Management**

- **FR-001**: The application MUST allow the user to create multiple independent projects, each identified by a unique UUID generated at creation time.
- **FR-002**: Each project MUST store mandatory metadata: Kunde (client name), Ersteller (creator name), and Adresse (address). All three fields MUST be non-empty before a project can be exported.
- **FR-003**: The user MUST be able to save a project as a local JSON file and reload it. The reload MUST restore all metadata, load series definitions, and time series data without loss.
- **FR-004**: The application MUST allow switching between projects without data loss.

**Load Series — SLP (BDEW)**

- **FR-005**: The user MUST be able to add a BDEW standard load profile by selecting a profile type from the set {H0, G0, G1, G2, G3, G4, G5, G6, L0, L1, L2} and entering an annual energy demand in kWh.
- **FR-006**: The system MUST scale the normalized BDEW profile so that its integral over the calendar year equals the entered annual energy demand (±0.1%).

**Load Series — CSV/XLSX Upload**

- **FR-007**: The user MUST be able to upload one or more CSV or XLSX files. Each file MUST be parsed into a load series with one value per time step for the full calendar year.
- **FR-008**: Missing or non-numeric values in uploaded files MUST be replaced with 0 kW. The user MUST be informed of the count of replaced values.
- **FR-009**: Multiple uploaded files MUST be combinable into a single summed series via a "gemeinsam verarbeiten" option.

**Load Series — Power Summary (PS)**

- **FR-010**: The user MUST be able to create a hierarchical PS structure containing groups, sub-groups, and leaf-level consumers.
- **FR-011**: Each PS consumer MUST have an assigned load profile type (from the BDEW set) and an annual energy demand in kWh.
- **FR-012**: Simultaneity factors in the range (0, 1] MUST be applicable at any group or sub-group level. The factor MUST multiply the aggregated power at that level at every time step.
- **FR-013**: The PS aggregate load series MUST be recomputed automatically whenever any consumer parameter or simultaneity factor changes.

**Load Series — PVA**

- **FR-014**: The user MUST be able to add a PV system by specifying peak power (kWp), azimuth (0–360°), and tilt angle (0–90°). Location/climate zone MUST default to a central-European profile if not specified.
- **FR-015**: The PV generation profile MUST produce non-positive values (generation convention) with zero values during night-time hours and a plausible annual yield.

**Load Series — BESS**

- **FR-016**: The user MUST be able to add a BESS by specifying capacity (kWh), maximum charge power (kW), maximum discharge power (kW), round-trip efficiency (%), and an operating strategy from {Peak Shaving, Eigenverbrauchsmaximierung, Arbitrage}.
- **FR-017**: The BESS simulation MUST enforce capacity and power constraints at every time step (state of charge: [0, capacity]; charge/discharge power: [−max_discharge, +max_charge]).
- **FR-018**: The BESS profile MUST be recomputed whenever any other load series in the project changes (since the net load curve changes).

**Combined View & Limits**

- **FR-019**: The application MUST combine all active load series into a single aggregated annual time series. Missing values (time steps not covered by a series) MUST be treated as 0 kW.
- **FR-020**: The user MUST be able to define static limit values (Sicherung, Hausanschluss, Trafo) in kW per project. These MUST be displayed as labelled horizontal lines in the chart.

**Visualization**

- **FR-021**: The application MUST display an interactive P(t) chart with time on the x-axis (full calendar year) and power in kW on the y-axis.
- **FR-022**: The chart MUST support toggling individual load series and category aggregates (SLP, CSV, PS, PVA, BESS, Gesamt) on/off via a legend.
- **FR-023**: The chart MUST support horizontal panning and time-axis zooming (scroll/pinch).

**Export**

- **FR-024**: The user MUST be able to export a semicolon-delimited CSV file containing all individual series and aggregated series as columns, with ISO 8601 timestamps in the first column and 0 for missing values.
- **FR-025**: The user MUST be able to export a JSON file containing the complete project definition (all parameters and time series data) that can be re-imported without data loss.

### Key Entities

- **Project**: UUID, Kunde, Ersteller, Adresse, list of LoadSeries, StaticLimits.
- **LoadSeries**: ID, name, type (SLP | CSV | PS | PVA | BESS), parameters (type-specific), resolved time series array (one value per time step).
- **SLPParameters**: profileType (BDEW code), annualEnergyKWh.
- **CSVParameters**: fileName(s), mergeMode (individual | combined), rawData reference.
- **PSNode**: type (group | consumer), name, children (groups/consumers), simultaneityFactor (groups only), profileType + annualEnergyKWh (consumers only).
- **PVAParameters**: peakPowerKWp, azimuthDeg, tiltDeg, climateZone.
- **BESSParameters**: capacityKWh, maxChargePowerKW, maxDischargePowerKW, efficiencyPct, strategy.
- **StaticLimits**: Sicherung (kW), Hausanschluss (kW), Trafo (kW) — all optional, displayed when set.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A planner can create a project, add at least one SLP load series, view the chart, and export both CSV and JSON within 5 minutes of opening the application for the first time, without any external documentation.
- **SC-002**: Round-trip project save/load (JSON export → JSON import) reproduces an identical application state: all metadata, load series parameters, and computed time series values match the original (±0.01 kW per step).
- **SC-003**: The annual energy integral of any SLP-based series matches the entered annual energy demand within ±0.1%.
- **SC-004**: The BESS simulation never violates capacity or power constraints at any of the 35040 time steps.
- **SC-005**: 100% of exported CSV rows contain numeric values (no empty cells); missing series values are represented as 0.

### Performance Acceptance Criteria *(mandatory — Constitution Principle IV)*

- **PERF-001**: Initial application load (all static assets including bundled BDEW profiles) MUST complete within 3 seconds on a standard broadband connection (≥10 Mbit/s).
- **PERF-002**: Adding or updating any load series (SLP, PVA, BESS recalculation) MUST produce a visible chart update within 1 second for a project with up to 10 load series.
- **PERF-003**: Uploading and parsing a CSV file of up to 10 MB MUST complete within 5 seconds without freezing the browser tab.
- **PERF-004**: The interactive chart MUST maintain smooth pan and zoom response (no perceptible lag) for a project with up to 10 load series over a full calendar year (35040 time steps each).
- **PERF-005**: Browser memory consumption MUST NOT exceed 500 MB for a project with 10 load series of 35040 steps each.

### UX Consistency Criteria *(mandatory — Constitution Principle III)*

- **UX-001**: All load series types use a consistent add/edit/delete interaction pattern (add button → parameter form → confirm → series appears in list).
- **UX-002**: All error and validation messages are displayed inline, in German, in plain language without technical jargon or stack traces.
- **UX-003**: All interactive controls (buttons, inputs, chart legend toggles) have visible focus states and are keyboard-navigable (WCAG 2.1 AA).
