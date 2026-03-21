# Tasks: SLP Clickdummy — Elektrische Lastgang-Verwaltung

**Input**: Design documents from `specs/001-slp-clickdummy/`
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅ · quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Tests are NOT included (none requested in spec).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths are included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository skeleton, tooling, and static data required before any feature work.

- [x] T001 Create full project directory structure: `src/models/`, `src/services/`, `src/generators/`, `src/ui/pages/`, `src/ui/components/`, `tests/unit/`, `tests/integration/`, `tests/benchmarks/`, `data/bdew/`
- [x] T002 Create `requirements.txt` with pinned runtime dependencies: streamlit≥1.32, pandas≥2.1, numpy≥1.26, plotly≥5.19, openpyxl≥3.1
- [x] T003 [P] Create `requirements-dev.txt` with dev dependencies: pytest≥8.0, pytest-cov≥4.1, pytest-benchmark≥4.0, hypothesis≥6.98, ruff≥0.3, black≥24.0, pre-commit≥3.6
- [x] T004 [P] Create `.pre-commit-config.yaml` with ruff and black hooks (Constitution I: Code Quality)
- [x] T005 [P] Create `pytest.ini` (or `pyproject.toml` `[tool.pytest.ini_options]`) enforcing `--cov=src --cov-fail-under=80` (Constitution II: Testing Standards)
- [x] T006 [P] Bundle all 11 BDEW normalised profiles as CSV files in `data/bdew/` (columns: `saison`, `tagesart`, `slot_index`, `value_kw_per_1000kwha`): `H0.csv`, `G0.csv`, `G1.csv`, `G2.csv`, `G3.csv`, `G4.csv`, `G5.csv`, `G6.csv`, `L0.csv`, `L1.csv`, `L2.csv`
- [x] T007 Create `app.py` as the Streamlit entry point: import and route to `ui/pages/project_page.py`; load BDEW profiles once into `st.session_state["bdew_profiles"]` at startup

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data model, session-state shape, normalizer, and aggregator. All user story phases depend on this phase being complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T008 [P] Implement all dataclasses and enums in `src/models/project.py`: `Project`, `StaticLimits`, `SeriesType`
- [x] T009 [P] Implement all dataclasses and enums in `src/models/load_series.py`: `LoadSeries`, `SLPParameters`, `CSVParameters`, `MergeMode`, `PSParameters`, `PVAParameters`, `BESSParameters`, `BESSStrategy`
- [x] T010 [P] Implement `PSNode` and `PSNodeType` dataclasses in `src/models/ps_node.py`
- [x] T011 Implement `Normalizer` class in `src/normalizer.py`: `canonical_index(target_year)` (35040-step UTC DatetimeIndex, Feb-29 exclusion), `align(series, target_year)` (resample → reindex → fill 0, raise on <35040 non-null), `merge_series(arrays, mode)` (INDIVIDUAL passthrough / COMBINED element-wise sum)
- [x] T012 Implement `Aggregator.compute(project)` in `src/aggregator.py` returning `AggregationResult` dataclass: per-category sums (SLP_SUM, CSV_SUM, PS_SUM, PVA_SUM, BESS_SUM), TOTAL, DataFrame indexed by `canonical_index`, `peak_kw`, `valley_kw`; missing steps filled with 0
- [x] T013 Create `src/ui/components/error_display.py`: `show_errors(errors: list[str])` renders inline German error messages via `st.error` without stack traces (UX-002)
- [x] T014 Create `src/ui/components/series_form.py`: shared add/edit form shell used by all series type pages — header, type selector, confirm/cancel buttons, consistent layout (UX-001)

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 — Projekt anlegen und Stammdaten pflegen (Priority: P1) 🎯 MVP

**Goal**: User can create a project with metadata, export it as JSON, and reimport it without data loss.

**Independent Test**: Create a project, fill Kunde/Ersteller/Adresse, export JSON, reimport, verify all metadata fields and empty load_series are reproduced identically.

### Implementation for User Story 1

- [x] T015 [P] [US1] Implement `ProjectService` in `src/services/project_service.py`: `create(kunde, ersteller, adresse, seed=None)` (UUID4, target_year=current_year−2, seed via secrets.randbelow), `validate_for_export(project)` (German error strings for empty fields), `to_json(project)` (schema v1.0 serialisation, raises ValueError if invalid), `from_json(raw_json)` (deserialise, skip unknown series_type with `_skipped_series` list, raise on malformed JSON or unknown schema_version), `switch_active(session_state, uuid)`
- [x] T016 [P] [US1] Implement `LoadRegistry` in `src/services/load_registry.py`: `add(project, series)` (append, recompute BESS), `update(project, series_id, new_parameters)` (recompute series + all BESS if non-BESS), `remove(project, series_id)` (recompute all BESS), `set_active(project, series_id, active)` (toggle + recompute BESS), `recompute_bess(project)` (net load → re-simulate all BESS in order)
- [x] T017 [US1] Implement `src/ui/pages/project_page.py`: sidebar project list (selectbox), "Neues Projekt erstellen" button (creates project, adds to `st.session_state["projects"]`, switches active), metadata form (Kunde/Ersteller/Adresse text inputs, save-to-session on change), "Projekt laden" file uploader (`ProjectService.from_json`, warns on skipped series), `st.download_button` for JSON export (calls `validate_for_export` first, shows errors via `error_display` if invalid)

**Checkpoint**: User Story 1 fully functional. A planner can create a project, fill metadata, export and reimport JSON independently.

---

## Phase 4: User Story 2 — Standardlastprofil (SLP / BDEW) hinzufügen (Priority: P2)

**Goal**: User can add a BDEW SLP profile by type and annual kWh; the resulting time series integrates to the entered energy within ±0.1%.

**Independent Test**: Add H0 with 5000 kWh/a; verify `values.sum() * 0.25 ≈ 5000` (±0.1%) and series appears in project list.

### Implementation for User Story 2

- [x] T018 [P] [US2] Implement `SLPGenerator.generate(params, target_year, bdew_profiles)` in `src/generators/slp_generator.py`: map each of 35040 steps to (saison, tagesart, slot_index), look up normalised value, apply H0 dynamisation factor F(d), scale by `annual_energy_kwh / 1000.0`; postcondition `values.sum() * 0.25 ≈ annual_energy_kwh` (±0.1%), all values ≥ 0
- [x] T019 [US2] Extend `src/ui/pages/series_page.py` with SLP sub-form (or create file if first use): profile type selectbox ({H0, G0, G1–G6, L0–L2}), annual energy number input, "Hinzufügen" button calling `SLPGenerator.generate` then `LoadRegistry.add`; edit inline by selecting existing series; display series list with delete button per entry (UX-001); warn if annual_energy_kwh == 0

**Checkpoint**: User Story 2 complete. Planners can add and edit SLP series and see them in the list.

---

## Phase 5: User Story 7 — Jahresdarstellung und interaktives Chart (Priority: P2)

**Goal**: All active load series shown in a single interactive Plotly chart with category toggles, limit lines, pan and zoom.

**Independent Test**: With at least one SLP series, open chart page; verify P(t) chart renders, limit lines appear, legend toggles hide/show series, and TOTAL recalculates.

**Note**: Priority P2 (co-equal with US2); depends on US2 for a meaningful chart.

### Implementation for User Story 7

- [x] T020 [P] [US7] Implement `PlotEngine.build_figure(result: AggregationResult, limits: StaticLimits, visible: dict) -> go.Figure` in `src/plot_engine.py`: `go.Scattergl` traces per active series and category sums; default visibility per `aggregator.md` legend mapping; `uirevision="constant"` for zoom/pan persistence; horizontal dashed `go.layout.Shape` + `go.layout.Annotation` for each non-None limit value; x-axis = full calendar year, y-axis = kW
- [x] T021 [US7] Implement `src/ui/pages/chart_page.py`: call `Aggregator.compute(project)`, call `PlotEngine.build_figure`, render via `st.plotly_chart(fig, use_container_width=True)`; category toggle checkboxes updating `st.session_state["chart_visible"]`; handle empty project (no series) by rendering chart with limit lines only

**Checkpoint**: User Story 7 complete. Planners see an interactive chart updating as series are added.

---

## Phase 6: User Story 3 — Messdaten-Upload (CSV/XLSX) (Priority: P3)

**Goal**: User can upload CSV or XLSX files; parsed values are aligned to the canonical grid; missing values replaced with 0 and reported; multiple files can be merged.

**Independent Test**: Upload a known CSV; verify parsed values match source (±0.01 kW/step), series appears in list, and replaced-zero count is reported.

### Implementation for User Story 3

- [x] T022 [P] [US3] Implement CSV/XLSX parser module in `src/generators/` as a standalone function (e.g., `parse_upload(file_bytes, filename, target_year, bdew_profiles=None) -> tuple[np.ndarray, CSVParameters]`) in `src/generators/csv_parser.py`: auto-detect encoding (UTF-8 → ISO-8859-1), separator (comma → semicolon), power column (first numeric column in [−10000, 10000] kW), timestamp column (pandas `to_datetime`); assume 15-min start at Jan 1 if no timestamp; resample/reindex to canonical grid via `Normalizer.align`; replace NaN with 0, count replacements; raise `ValueError` with German message if row count after alignment < 35040; support XLSX via `openpyxl` engine; show `st.warning` + confirmation dialog for files > 50 MB
- [x] T023 [US3] Extend `src/ui/pages/series_page.py` with CSV/XLSX sub-form: `st.file_uploader` (accept `.csv`, `.xlsx`, multiple=True), merge mode toggle ("gemeinsam verarbeiten"), parse via `csv_parser.parse_upload`, apply `Normalizer.merge_series` for COMBINED mode, call `LoadRegistry.add`; display replaced-zero warning with count (UX-002); display resolution-mismatch error inline in German

**Checkpoint**: User Story 3 complete. Planners can upload measured data files.

---

## Phase 7: User Story 8 — Daten exportieren (Priority: P3)

**Goal**: User can export wide-format semicolon CSV and full project JSON from the export page.

**Independent Test**: With one SLP series, trigger both exports; CSV has correct headers, 35040 rows, no empty cells, correct TOTAL; JSON reimports without data loss.

**Note**: Priority P3 (co-equal with US3); depends on US1 (project metadata) for JSON validation.

### Implementation for User Story 8

- [x] T024 [P] [US8] Implement `ExportEngine` in `src/export_engine.py`: `to_csv_bytes(result: AggregationResult) -> bytes` (UTF-8 BOM, semicolon delimiter, ISO 8601 UTC timestamp column, 35040 data rows, 0.0 for missing, column order per contract), `to_json_bytes(project: Project) -> bytes` (delegates to `ProjectService.to_json`, returns UTF-8 bytes, raises German `ValueError` if validation fails); suggested filenames per contract
- [x] T025 [US8] Implement `src/ui/pages/export_page.py`: call `ProjectService.validate_for_export`; if invalid show errors via `error_display`; if valid render two `st.download_button` widgets — CSV (calls `Aggregator.compute` then `ExportEngine.to_csv_bytes`) and JSON (calls `ExportEngine.to_json_bytes`); handle empty-series project (CSV with headers only, valid JSON)

**Checkpoint**: User Story 8 complete. Both export formats available and verifiable.

---

## Phase 8: User Story 4 — Power Summary (PS) modellieren (Priority: P4)

**Goal**: User can build a hierarchical group/consumer structure with simultaneity factors; the aggregated series equals `GLF × sum(child_series)` at every step.

**Independent Test**: Create group with two H0 consumers (3000 kWh/a each), GLF=0.8; verify every step of PS series equals 0.8 × (series1 + series2).

### Implementation for User Story 4

- [x] T026 [P] [US4] Implement `PSBuilder.build(params: PSParameters, target_year: int, bdew_profiles: dict) -> np.ndarray` in `src/generators/ps_builder.py`: depth-first post-order traversal; CONSUMER leaves call `SLPGenerator.generate`; GROUP nodes sum children element-wise then multiply by `simultaneity_factor`; validate `simultaneity_factor ∈ (0, 1]` (raise `ValueError` with German message on 0 or negative); return root array of shape (35040,)
- [x] T027 [US4] Extend `src/ui/pages/series_page.py` with PS sub-form: tree editor (add group / add sub-group / add consumer with profile_type + annual_energy_kwh + name); simultaneity factor input per group (validate (0, 1], warn if >1); "Berechnen" button calls `PSBuilder.build` then `LoadRegistry.add`; on any parameter change trigger rebuild via `LoadRegistry.update`; display PS series as single named curve in list

**Checkpoint**: User Story 4 complete. Planners can model hierarchical consumption structures.

---

## Phase 9: User Story 5 — Photovoltaikanlage (PVA) hinzufügen (Priority: P5)

**Goal**: User can add a PV system; the generated profile has ≤ 0 kW values, zero at night, and plausible annual yield (900–1100 kWh/kWp/a).

**Independent Test**: Add 10 kWp south-facing (azimuth=180°, tilt=30°); verify all values ≤ 0, night slots = 0.0, `abs(values).sum() * 0.25 ∈ [9000, 11000]`.

### Implementation for User Story 5

- [x] T028 [P] [US5] Implement `PVGenerator.generate(params: PVAParameters, target_year: int, seed: int) -> np.ndarray` in `src/generators/pv_generator.py`: trigonometric solar model per `research.md §3` (declination, hour angle, cos(zenith), tilt/azimuth transposition, clearsky seasonal envelope); cloud-cover variation via `numpy.random.Generator(seed)`; output all values ≤ 0 (generation convention); night-time (astronomical darkness) exactly 0.0; annual yield ∈ [900, 1100] kWh/kWp/a for central_europe defaults; deterministic for fixed (params, target_year, seed)
- [x] T029 [US5] Extend `src/ui/pages/series_page.py` with PVA sub-form: peak power (kWp) number input (>0, warn if 0), azimuth selectbox/slider (0–360°), tilt slider (0–90°), climate zone (default "central_europe"); "Hinzufügen" calls `PVGenerator.generate` then `LoadRegistry.add`; on parameter change calls `LoadRegistry.update` (which then recomputes all BESS)

**Checkpoint**: User Story 5 complete. PV generation series can be added and appear as negative load in chart.

---

## Phase 10: User Story 6 — Batteriespeichersystem (BESS) hinzufügen (Priority: P6)

**Goal**: User can add a BESS; simulation respects capacity/power constraints at all 35040 steps; profile recomputes when any other series changes.

**Independent Test**: Add BESS (100 kWh, 50 kW, 90%) with Peak Shaving to a project with an SLP series; verify `|values[t]| ≤ 50` for all t, SOC stays in [0, 100], and combined peak ≤ original peak.

### Implementation for User Story 6

- [x] T030 [P] [US6] Implement `BESSSimulator.simulate(params: BESSParameters, net_load: np.ndarray) -> np.ndarray` in `src/generators/bess_simulator.py`: forward pass over 35040 steps; strategy dispatch functions (Peak Shaving: clip net > threshold; Eigenverbrauch: charge on PV surplus, discharge when PV insufficient; Arbitrage: charge 00:00–06:00, discharge 17:00–21:00 via seed-deterministic price curve); symmetric efficiency split (η_charge=1/√η, η_discharge=√η); clip actual dispatch to [−max_charge, +max_discharge]; clip SOC to [0, capacity]; auto-compute peak_shaving_threshold_kw as 90th percentile of net_load if None; warn (but do not block) if net_load is all-zero
- [x] T031 [US6] Extend `src/ui/pages/series_page.py` with BESS sub-form: capacity (kWh), max charge power (kW), max discharge power (kW), efficiency (0–100%), strategy selectbox (Peak Shaving / Eigenverbrauchsmaximierung / Arbitrage), optional peak-shaving threshold; "Hinzufügen" calls `LoadRegistry.add` which calls `BESSSimulator.simulate` via `recompute_bess`; display German warning if project has no non-BESS active series at time of add; recomputation is automatic via `LoadRegistry` on any upstream series change

**Checkpoint**: User Story 6 complete. Full feature set available: SLP + CSV + PS + PVA + BESS + Chart + Export.

---

## Phase 11: Limits UI — Statische Grenzwerte (FR-020)

**Purpose**: Allow users to set and update static limit values (Sicherung, Hausanschluss, Trafo) displayed as dashed lines in the chart. Cross-cutting concern for US7.

- [x] T032 Implement `src/ui/pages/limits_page.py`: three optional float number inputs (Sicherung kW, Hausanschluss kW, Trafo kW); save to `project.static_limits` in session state; `None` when field is cleared; changes trigger chart re-render on next navigation to chart page
- [x] T033 Wire navigation in `app.py` to include all five pages: Projekt, Lastgänge (series_page), Grenzwerte (limits_page), Chart, Export — via `st.sidebar.radio` or `st.tabs`

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Final quality pass across all delivered user stories.

- [x] T034 [P] Verify all public functions and classes in `src/` have docstrings (Constitution I: Code Quality); run `ruff check src/ tests/` and fix any remaining lint errors
- [x] T035 [P] Run `pytest --cov=src --cov-report=term-missing`; confirm coverage ≥ 80%; add `# nocover` pragmas only on genuinely untestable I/O lines (Constitution II: Testing Standards)
- [x] T036 [P] Run benchmarks in `tests/benchmarks/bench_generators.py` (PERF-002: chart update ≤ 1 s for ≤ 10 series), `tests/benchmarks/bench_csv_parse.py` (PERF-003: 10 MB ≤ 5 s), `tests/benchmarks/bench_aggregator.py` (PERF-004: 10 × 35040 aggregation); record and commit results (Constitution IV: Performance)
- [x] T037 [P] UX consistency review: confirm all five series type sub-forms follow identical add → form → confirm → list pattern (UX-001); confirm all error messages are German, inline, no stack traces (UX-002); document known WCAG 2.1 AA gap (Streamlit focus order) in `plan.md` Complexity Tracking (UX-003; Constitution III: UX Consistency)
- [x] T038 Validate `quickstart.md` end-to-end: fresh venv → `pip install -r requirements.txt` → `streamlit run app.py` → create project → add SLP → view chart → export CSV and JSON — all within 3 s startup (PERF-001)
- [x] T039 [P] Add benchmark scaffold files: `tests/benchmarks/bench_generators.py`, `tests/benchmarks/bench_csv_parse.py`, `tests/benchmarks/bench_aggregator.py` (create empty files with fixture stubs if not yet created during story phases)
- [x] T040 [P] Add integration test files per plan.md: `tests/integration/test_project_roundtrip.py` (SC-002), `tests/integration/test_slp_integral.py` (SC-003), `tests/integration/test_bess_constraints.py` (SC-004), `tests/integration/test_csv_export.py` (SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user story phases**
- **US1 (Phase 3)**: Depends on Phase 2 — no story dependencies
- **US2 (Phase 4)**: Depends on Phase 2 — no story dependencies
- **US7 (Phase 5)**: Depends on Phase 2 + US2 (needs at least one series type for meaningful chart)
- **US3 (Phase 6)**: Depends on Phase 2 — no story dependencies
- **US8 (Phase 7)**: Depends on Phase 2 + US1 (project validation) — benefits from US2/US3 for content
- **US4 (Phase 8)**: Depends on Phase 2 + US2 (`SLPGenerator` reused by `PSBuilder`)
- **US5 (Phase 9)**: Depends on Phase 2 — no story dependencies
- **US6 (Phase 10)**: Depends on Phase 2 + at least one of US2/US3/US4/US5 for meaningful BESS
- **Limits UI (Phase 11)**: Depends on US7 (chart renders limit lines)
- **Polish (Phase 12)**: Depends on all story phases

### User Story Dependencies

| Story | Depends On | Independent? |
|---|---|---|
| US1 — Project Management | Phase 2 | ✅ Fully independent |
| US2 — SLP | Phase 2 | ✅ Fully independent |
| US7 — Chart | Phase 2, US2 | ✅ Independently testable after US2 |
| US3 — CSV/XLSX | Phase 2 | ✅ Fully independent |
| US8 — Export | Phase 2, US1 | ✅ Testable with any one series type |
| US4 — PS | Phase 2, US2 (SLPGenerator) | ✅ Independently testable |
| US5 — PVA | Phase 2 | ✅ Fully independent |
| US6 — BESS | Phase 2, any upstream series | ✅ Testable with SLP series |

### Within Each Phase

- [P]-marked tasks within a phase can run in parallel
- Models/dataclasses (T008–T010) must be complete before services consume them
- `Normalizer` (T011) must be complete before any generator that calls it
- `Aggregator` (T012) must be complete before `PlotEngine` and `ExportEngine`

---

## Parallel Execution Examples

### Phase 2 Parallel Window

```
T008 src/models/project.py          ─┐
T009 src/models/load_series.py      ─┤─ all parallel
T010 src/models/ps_node.py          ─┘
     ↓ (all complete)
T011 src/normalizer.py              ─┐
T012 src/aggregator.py              ─┤─ parallel (T012 can start once T008-T010 done)
T013 src/ui/components/error_display.py ─┤
T014 src/ui/components/series_form.py   ─┘
```

### User Story Phase Parallel Window (after Phase 2)

```
T015 src/services/project_service.py   ─┐ US1 parallel
T016 src/services/load_registry.py     ─┘

T018 src/generators/slp_generator.py   ─┐ US2 parallel with US1
     ↓ (T018 done)
T019 src/ui/pages/series_page.py (SLP) ─┘

T022 src/generators/csv_parser.py      ─── US3 parallel with US1 & US2

T024 src/export_engine.py              ─── US8 parallel generator task

T026 src/generators/ps_builder.py      ─── US4 parallel with US3 (after T018)

T028 src/generators/pv_generator.py    ─── US5 parallel with all above

T030 src/generators/bess_simulator.py  ─── US6 parallel generator task
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**CRITICAL — blocks everything**)
3. Complete Phase 3: User Story 1 (T015–T017)
4. **STOP and VALIDATE**: Create project → fill metadata → export JSON → reimport → verify round-trip
5. Demo-ready as a project registry

### Incremental Delivery

1. Phase 1 + 2 → Foundation ✅
2. Phase 3 (US1) → Project management → **MVP checkpoint**
3. Phase 4 (US2) + Phase 5 (US7) → First load series + chart → **Visible value**
4. Phase 6 (US3) + Phase 7 (US8) → Measured data + exports → **Client-handoff ready**
5. Phase 8 (US4) → Power Summary → **Structured modelling**
6. Phase 9 (US5) → PV generation → **Modern energy planning**
7. Phase 10 (US6) → BESS simulation → **Full feature set**
8. Phase 11 + 12 → Limits UI + Polish → **Production-ready**

---

## Notes

- [P] = tasks in different files with no dependencies on incomplete tasks; safe to run in parallel
- [Story] label maps each task to its user story for traceability and independent delivery
- All generator tasks (T018, T022, T026, T028, T030) are pure-function implementations — independently testable without the UI
- `LoadRegistry.recompute_bess` is the reactivity hub: called automatically by `add`, `update`, `remove`, `set_active`
- BDEW profiles are loaded once at startup into `st.session_state["bdew_profiles"]` and never reloaded; generators accept them as a parameter (no global state)
- Target year = `current_year − 2` is set at project creation and stored in JSON; never recalculated
- Avoid vague tasks; avoid cross-story file conflicts; commit after each logical group or checkpoint
