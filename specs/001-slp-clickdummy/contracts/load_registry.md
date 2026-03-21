# Contract: LoadRegistry

**Module**: `src/services/load_registry.py`  
**Date**: 2026-03-21

---

## Responsibilities

- Central CRUD store for `LoadSeries` objects within a project
- Triggers recomputation of dependent series on parameter change
- Enforces insertion order (collision resolution: last added wins)

---

## Interface

### `LoadRegistry.add(project: Project, series: LoadSeries) -> Project`

Appends a new `LoadSeries` to `project.load_series`. The series MUST already have
its `values` array computed (caller passes a fully-resolved series).

**Preconditions**: `series.id` is unique within `project.load_series`  
**Postconditions**: `series` appears at the end of `project.load_series`; if `series.series_type == BESS`, triggers `recompute_bess(project)` for all existing BESS series  
**Raises**: `ValueError` if `series.id` already exists in the project

---

### `LoadRegistry.update(project: Project, series_id: str, new_parameters) -> Project`

Replaces the parameters of an existing `LoadSeries` and recomputes its `values`.

**Preconditions**: `series_id` exists in `project.load_series`  
**Postconditions**:
- The series `parameters` are replaced with `new_parameters`
- `values` is recomputed by calling the appropriate generator
- If the updated series is not BESS, all BESS series in the project are recomputed afterwards (net load changed)
- If the updated series is BESS, only that BESS series is recomputed  

**Raises**: `KeyError` if `series_id` not found; `ValueError` if `new_parameters` fail validation

---

### `LoadRegistry.remove(project: Project, series_id: str) -> Project`

Removes the `LoadSeries` with the given ID.

**Preconditions**: `series_id` exists in `project.load_series`  
**Postconditions**: series removed; all BESS series recomputed (net load changed)  
**Raises**: `KeyError` if `series_id` not found

---

### `LoadRegistry.set_active(project: Project, series_id: str, active: bool) -> Project`

Toggles the `is_active` flag of a series.

**Postconditions**: `series.is_active` updated; all BESS series recomputed  
**Raises**: `KeyError` if `series_id` not found

---

### `LoadRegistry.recompute_bess(project: Project) -> Project`

Recomputes all BESS series in order using the current net load curve
(sum of all non-BESS, active series after normalisation and aggregation).

**Postconditions**: all BESS `values` arrays are updated in-place  
**Note**: called automatically by `add`, `update`, `remove`, `set_active` whenever the net load may have changed

---

## Recompute Dependency Graph

```
Parameter change on SLP/CSV/PS/PVA series
    → recompute that series
    → recompute net load curve (Aggregator)
    → recompute all BESS series (in order)

Parameter change on BESS series
    → recompute that BESS series only (net load unchanged)

Series added (any type)
    → compute new series values
    → recompute all BESS series

Series removed (any type)
    → recompute all BESS series
```
