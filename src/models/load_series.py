"""Data models for load series and their parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.models.project import SeriesType


class MergeMode(str, Enum):
    """Merge mode for CSV/XLSX uploads with multiple files."""

    INDIVIDUAL = "INDIVIDUAL"
    COMBINED = "COMBINED"


class BESSStrategy(str, Enum):
    """BESS dispatch strategy."""

    PEAK_SHAVING = "PEAK_SHAVING"
    EIGENVERBRAUCH = "EIGENVERBRAUCH"
    ARBITRAGE = "ARBITRAGE"


@dataclass
class SLPParameters:
    """Parameters for a BDEW Standard Load Profile series."""

    profile_type: str
    annual_energy_kwh: float


@dataclass
class CSVParameters:
    """Parameters for a CSV/XLSX upload series."""

    source_filenames: list[str]
    merge_mode: MergeMode
    column_name: str
    replaced_zeros: int


@dataclass
class PSParameters:
    """Parameters for a Power Summary hierarchical model series."""

    root_node: object


@dataclass
class PVAParameters:
    """Parameters for a photovoltaic generation series."""

    peak_power_kwp: float
    azimuth_deg: float
    tilt_deg: float
    climate_zone: str = "central_europe"


@dataclass
class BESSParameters:
    """Parameters for a Battery Energy Storage System series."""

    capacity_kwh: float
    max_charge_power_kw: float
    max_discharge_power_kw: float
    efficiency_pct: float
    strategy: BESSStrategy
    peak_shaving_threshold_kw: float | None = None


@dataclass
class LoadSeries:
    """A single named load series with its computed values."""

    id: str
    name: str
    series_type: SeriesType
    parameters: SLPParameters | CSVParameters | PSParameters | PVAParameters | BESSParameters
    values: list[float]
    is_active: bool = True
