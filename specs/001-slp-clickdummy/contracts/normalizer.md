# Contract: Normalizer

**Module**: `src/normalizer.py`  
**Date**: 2026-03-21

---

## Responsibilities

- Define and expose the canonical 15-minute UTC time grid for a given target year
- Map uploaded or generated time series onto this grid
- Apply ISO-week KW53→KW52 mapping, leap-day removal, collision resolution, and gap filling

---

## Interface

### `Normalizer.canonical_index(target_year: int) -> pd.DatetimeIndex`

Returns the canonical 35040-step DatetimeIndex.

```
freq = "15min"
start = f"{target_year}-01-01 00:00:00"
end   = f"{target_year}-12-31 23:45:00"
tz    = "UTC"
```

**Leap years**: The index always has 35040 entries. Feb 29 is excluded via
`index[~((index.month == 2) & (index.day == 29))]`.

**Postconditions**: `len(result) == 35040`; `result.tz == UTC`; no Feb 29 entries

---

### `Normalizer.align(series: pd.Series, target_year: int) -> np.ndarray`

Aligns an arbitrary `pd.Series` (with a DatetimeIndex) onto the canonical grid.

**Steps**:
1. Convert index to UTC if timezone-naive (assume UTC).
2. Resample to 15-min if needed (mean aggregation).
3. Reindex to `canonical_index(target_year)`.
4. Remove Feb 29 entries.
5. Fill NaN with 0.0.

**Postconditions**: `result.shape == (35040,)`; no NaN values  
**Raises**: `ValueError` if `series` has fewer than 35040 non-null values after resampling (resolution mismatch — caller must display error to user)

---

### `Normalizer.merge_series(arrays: list[np.ndarray], mode: MergeMode) -> np.ndarray`

Combines multiple aligned arrays.

- `INDIVIDUAL`: returns the arrays unchanged (list passthrough — caller stores each separately)
- `COMBINED`: returns element-wise sum of all arrays

**Preconditions**: all arrays in `arrays` have shape `(35040,)`  
**Raises**: `ValueError` if any array has wrong shape

---

## ISO-Week / KW53 Mapping (SLP-specific)

Used by `SLPGenerator`, not directly by `Normalizer`, but documented here for
consistency:

- ISO week 53 (only occurs in some years): treated as KW52 (last regular week).
- Result: the last 7 days of a KW53 year reuse the KW52 BDEW lookup values.
- This is the BDEW-recommended approach for normalised profiles.

---

## Collision and Gap Rules

Applied during `LoadRegistry` aggregation (not in `Normalizer` directly), but
`Normalizer.canonical_index` is the authoritative grid both use:

| Situation | Rule |
|---|---|
| Multiple series cover the same time step | Last-added series value wins (insertion order) |
| No series covers a time step | Value = 0.0 kW |
| Series has NaN at a step after alignment | Treated as 0.0 kW |
