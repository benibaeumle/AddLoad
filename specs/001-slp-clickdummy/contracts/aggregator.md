# Contract: Aggregator

**Module**: `src/aggregator.py`  
**Date**: 2026-03-21

---

## Responsibilities

- Compute per-category sum arrays from all active `LoadSeries` in a project
- Compute the TOTAL net curve
- Produce a combined `pd.DataFrame` suitable for chart rendering and CSV export

---

## Interface

### `Aggregator.compute(project: Project) -> AggregationResult`

Computes all category sums and TOTAL from the active load series in `project`.

**Algorithm**:
1. Filter `project.load_series` to `is_active == True`.
2. For each category `{SLP, CSV, PS, PVA, BESS}`: sum the `values` arrays of all
   active series of that type element-wise. If no series of that type is active,
   the category sum is a zero array.
3. Compute `TOTAL = CSV_SUM + SLP_SUM + PS_SUM + PVA_SUM + BESS_SUM`.
   (PVA values are already negative, so PV generation naturally reduces TOTAL.)
4. Build a `pd.DataFrame` indexed by `canonical_index(project.target_year)` with
   columns: one per active `LoadSeries` (by name), plus `CSV_SUM`, `SLP_SUM`,
   `PS_SUM`, `PVA_SUM`, `BESS_SUM`, `TOTAL`.

**Preconditions**: all active `LoadSeries.values` have shape `(35040,)`  
**Postconditions**:
- `result.df.shape == (35040, n_active_series + 6)`
- No NaN values in `result.df`
- `result.df["TOTAL"]` equals element-wise sum of all 5 category columns

**Raises**: `ValueError` if any active series `values` array has wrong shape

---

## AggregationResult

```python
@dataclass
class AggregationResult:
    df: pd.DataFrame          # Shape (35040, n_cols); index = canonical DatetimeIndex
    category_sums: dict       # {"CSV_SUM": np.ndarray, "SLP_SUM": ..., ...}
    total: np.ndarray         # Shape (35040,); TOTAL net curve
    peak_kw: float            # max(total) — used for BESS threshold default
    valley_kw: float          # min(total)
```

---

## Column Order in DataFrame

Individual series columns appear in insertion order (matching `project.load_series`
order, filtered to active). Aggregate columns always appear last in fixed order:

```
[individual series...] | CSV_SUM | SLP_SUM | PS_SUM | PVA_SUM | BESS_SUM | TOTAL
```

---

## Chart Legend Mapping

| DataFrame column | Default visibility in chart |
|---|---|
| Individual SLP series | Hidden (shown via category toggle) |
| Individual CSV series | Hidden |
| Individual PS series | Hidden |
| Individual PVA series | Hidden |
| Individual BESS series | Hidden |
| CSV_SUM | Visible |
| SLP_SUM | Visible |
| PS_SUM | Visible |
| PVA_SUM | Visible |
| BESS_SUM | Visible |
| TOTAL | Visible (bold line) |

Individual series can be toggled on via the chart legend. This visibility state is
stored in `st.session_state["chart_visible"]`.
