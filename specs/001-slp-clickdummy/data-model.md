# Data Model: SLP Clickdummy

**Branch**: `001-slp-clickdummy` | **Date**: 2026-03-21

---

## 1. Domain Model (Python Dataclasses)

### Project

```python
@dataclass
class Project:
    uuid: str                        # UUID4 string, immutable after creation
    schema_version: str              # "1.0" — for future migration
    seed: int                        # Integer seed for deterministic PV/BESS stochastics
    kunde: str                       # Mandatory — client name
    ersteller: str                   # Mandatory — creator name
    adresse: str                     # Mandatory — project address
    static_limits: StaticLimits
    load_series: list[LoadSeries]    # Ordered; order determines collision resolution
    created_at: str                  # ISO 8601 UTC timestamp
    target_year: int                 # current_year - 2 at creation time
```

### StaticLimits

```python
@dataclass
class StaticLimits:
    sicherung_kw: float | None    # Fuse limit in kW; None = not set / not displayed
    hausanschluss_kw: float | None
    trafo_kw: float | None
```

### LoadSeries

```python
@dataclass
class LoadSeries:
    id: str                          # UUID4 string
    name: str                        # Display name (user-editable)
    series_type: SeriesType          # Enum: SLP | CSV | PS | PVA | BESS
    parameters: SLPParameters | CSVParameters | PSParameters | PVAParameters | BESSParameters
    values: list[float]              # 35040 floats (kW); computed; always present after creation
    is_active: bool                  # Whether included in aggregation and chart (default True)
```

### SeriesType Enum

```python
class SeriesType(str, Enum):
    SLP  = "SLP"
    CSV  = "CSV"
    PS   = "PS"
    PVA  = "PVA"
    BESS = "BESS"
```

### SLPParameters

```python
@dataclass
class SLPParameters:
    profile_type: str      # One of: H0, G0, G1, G2, G3, G4, G5, G6, L0, L1, L2
    annual_energy_kwh: float  # > 0; annual demand to scale to
```

### CSVParameters

```python
@dataclass
class CSVParameters:
    source_filenames: list[str]   # Original filename(s); for display only
    merge_mode: MergeMode         # Enum: INDIVIDUAL | COMBINED
    column_name: str              # Detected power column name (for audit trail)
    replaced_zeros: int           # Count of values replaced with 0 during parsing
```

### MergeMode Enum

```python
class MergeMode(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    COMBINED   = "COMBINED"
```

### PSParameters

```python
@dataclass
class PSParameters:
    root_node: PSNode    # Serialised tree root
```

### PSNode

```python
@dataclass
class PSNode:
    node_id: str                  # UUID4
    node_type: PSNodeType         # Enum: GROUP | CONSUMER
    name: str
    # GROUP fields
    simultaneity_factor: float    # (0, 1]; default 1.0; only used if node_type == GROUP
    children: list[PSNode]        # Empty for CONSUMER nodes
    # CONSUMER fields
    profile_type: str | None      # BDEW code; only set for CONSUMER
    annual_energy_kwh: float | None  # > 0; only set for CONSUMER
```

### PSNodeType Enum

```python
class PSNodeType(str, Enum):
    GROUP    = "GROUP"
    CONSUMER = "CONSUMER"
```

### PVAParameters

```python
@dataclass
class PVAParameters:
    peak_power_kwp: float    # > 0
    azimuth_deg: float       # 0–360 (0=N, 90=E, 180=S, 270=W)
    tilt_deg: float          # 0–90 (0=horizontal, 90=vertical)
    climate_zone: str        # Default: "central_europe"; future: NUTS2 codes
```

### BESSParameters

```python
@dataclass
class BESSParameters:
    capacity_kwh: float          # > 0
    max_charge_power_kw: float   # > 0
    max_discharge_power_kw: float  # > 0
    efficiency_pct: float        # 0–100
    strategy: BESSStrategy       # Enum
    peak_shaving_threshold_kw: float | None  # Auto-computed if None (90th percentile)
```

### BESSStrategy Enum

```python
class BESSStrategy(str, Enum):
    PEAK_SHAVING         = "PEAK_SHAVING"
    EIGENVERBRAUCH       = "EIGENVERBRAUCH"
    ARBITRAGE            = "ARBITRAGE"
```

---

## 2. JSON Schema v1.0

The project JSON file is the canonical persistence format. All fields are required
unless marked `(optional)`.

```json
{
  "schema_version": "1.0",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "seed": 42,
  "kunde": "Musterkunde GmbH",
  "ersteller": "Max Mustermann",
  "adresse": "Musterstraße 1, 12345 Musterstadt",
  "created_at": "2026-03-21T10:00:00Z",
  "target_year": 2024,
  "static_limits": {
    "sicherung_kw": 100.0,
    "hausanschluss_kw": 250.0,
    "trafo_kw": null
  },
  "load_series": [
    {
      "id": "a1b2c3d4-...",
      "name": "SLP H0 – 5000 kWh/a",
      "series_type": "SLP",
      "is_active": true,
      "parameters": {
        "profile_type": "H0",
        "annual_energy_kwh": 5000.0
      },
      "values": [0.432, 0.421, "...35040 floats..."]
    },
    {
      "id": "b2c3d4e5-...",
      "name": "Messdaten Upload 1",
      "series_type": "CSV",
      "is_active": true,
      "parameters": {
        "source_filenames": ["messung_2024.csv"],
        "merge_mode": "INDIVIDUAL",
        "column_name": "P_kW",
        "replaced_zeros": 12
      },
      "values": [0.0, 0.0, "...35040 floats..."]
    },
    {
      "id": "c3d4e5f6-...",
      "name": "Verbrauchsstruktur Büro",
      "series_type": "PS",
      "is_active": true,
      "parameters": {
        "root_node": {
          "node_id": "...",
          "node_type": "GROUP",
          "name": "Bürogebäude",
          "simultaneity_factor": 0.85,
          "children": [
            {
              "node_id": "...",
              "node_type": "CONSUMER",
              "name": "Büro EG",
              "simultaneity_factor": 1.0,
              "children": [],
              "profile_type": "G1",
              "annual_energy_kwh": 12000.0
            }
          ],
          "profile_type": null,
          "annual_energy_kwh": null
        }
      },
      "values": [0.0, "...35040 floats..."]
    },
    {
      "id": "d4e5f6g7-...",
      "name": "PVA 20 kWp Süd",
      "series_type": "PVA",
      "is_active": true,
      "parameters": {
        "peak_power_kwp": 20.0,
        "azimuth_deg": 180.0,
        "tilt_deg": 30.0,
        "climate_zone": "central_europe"
      },
      "values": [0.0, 0.0, "...35040 floats (≤ 0)..."]
    },
    {
      "id": "e5f6g7h8-...",
      "name": "BESS 100 kWh Peak Shaving",
      "series_type": "BESS",
      "is_active": true,
      "parameters": {
        "capacity_kwh": 100.0,
        "max_charge_power_kw": 50.0,
        "max_discharge_power_kw": 50.0,
        "efficiency_pct": 90.0,
        "strategy": "PEAK_SHAVING",
        "peak_shaving_threshold_kw": 180.0
      },
      "values": [0.0, "...35040 floats..."]
    }
  ]
}
```

---

## 3. Session State Shape (Streamlit)

```python
st.session_state = {
    "projects": {
        "<uuid>": Project,   # All loaded projects, keyed by UUID
        ...
    },
    "active_project_uuid": str | None,   # UUID of currently selected project
    "bdew_profiles": {
        "H0": pd.DataFrame,  # Columns: saison, tagesart, slot_index, value
        "G0": pd.DataFrame,
        ...
    },
    "chart_visible": {
        "<series_id>": bool,   # Legend toggle state per series
        ...
    },
}
```

---

## 4. Wide CSV Export Format

```
timestamp;SLP H0 – 5000 kWh/a;Messdaten Upload 1;...;CSV_SUM;SLP_SUM;PS_SUM;PVA_SUM;BESS_SUM;TOTAL
2024-01-01T00:00:00Z;0.432;0.0;...;0.0;0.432;0.0;0.0;0.0;0.432
2024-01-01T00:15:00Z;0.421;0.0;...;0.0;0.421;0.0;0.0;0.0;0.421
...
```

- Encoding: UTF-8 with BOM
- Delimiter: `;`
- Decimal separator: `.` (dot)
- All 35040 rows present; no empty cells

---

## 5. Migration Strategy

`schema_version` field enables forward-compatible loading:

```python
LOADERS = {
    "1.0": load_v1,
}

def load_project(raw: dict) -> Project:
    version = raw.get("schema_version", "1.0")
    loader = LOADERS.get(version)
    if loader is None:
        raise ValueError(f"Unbekannte Schema-Version: {version}")
    return loader(raw)
```

Unknown `series_type` values inside `load_series` are skipped with a
`st.warning` per entry; the rest of the project loads normally.
