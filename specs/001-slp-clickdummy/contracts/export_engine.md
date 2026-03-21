# Contract: ExportEngine

**Module**: `src/export_engine.py`  
**Date**: 2026-03-21

---

## Responsibilities

- Produce the wide-format semicolon-delimited CSV bytes for time series export
- Produce the JSON bytes for project definition export
- Both outputs are returned as `bytes` for use with `st.download_button`

---

## Interface

### `ExportEngine.to_csv_bytes(result: AggregationResult) -> bytes`

Produces UTF-8 with BOM CSV bytes from the aggregation result DataFrame.

**Format**:
- Delimiter: `;`
- Decimal separator: `.`
- Timestamp column: `"timestamp"`, ISO 8601 UTC (e.g. `2024-01-01T00:00:00Z`)
- All 35040 rows present
- No empty cells; missing values are `0.0`
- Encoding: UTF-8 with BOM (`\xef\xbb\xbf`) for Excel compatibility
- Column order: `timestamp` first, then individual series (insertion order), then
  `CSV_SUM`, `SLP_SUM`, `PS_SUM`, `PVA_SUM`, `BESS_SUM`, `TOTAL`

**Preconditions**: `result.df` has no NaN values  
**Postconditions**:
- Row count = 35040 data rows + 1 header row
- Sum of any individual series column equals the corresponding `LoadSeries.values` sum (±1e-6)
- Sum of `TOTAL` column equals `result.total.sum()` (±1e-6)

**Raises**: nothing (always produces valid output if preconditions met)

---

### `ExportEngine.to_json_bytes(project: Project) -> bytes`

Serialises the project to UTF-8 JSON bytes using `ProjectService.to_json`.

**Preconditions**: `ProjectService.validate_for_export(project)` returns `[]`  
**Postconditions**:
- Output is valid UTF-8 JSON
- `ProjectService.from_json(output.decode("utf-8"))` reproduces an identical `Project`
- `schema_version` field is present and equals `"1.0"`

**Raises**: `ValueError` (German message) if validation fails

---

## Download Filenames

| Export type | Suggested filename |
|---|---|
| CSV | `slp_export_{project.uuid[:8]}_{target_year}.csv` |
| JSON | `projekt_{project.uuid[:8]}.json` |

These are suggestions passed to `st.download_button(file_name=...)`. The user may
rename the downloaded file in their browser's save dialog.
