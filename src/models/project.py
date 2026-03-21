"""Data model for Project and related types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SeriesType(str, Enum):
    """Enumeration of load series source types."""

    SLP = "SLP"
    CSV = "CSV"
    PS = "PS"
    PVA = "PVA"
    BESS = "BESS"


@dataclass
class StaticLimits:
    """Static power limit values displayed as horizontal lines in the chart."""

    sicherung_kw: float | None = None
    hausanschluss_kw: float | None = None
    trafo_kw: float | None = None


@dataclass
class Project:
    """Top-level project container holding metadata and all load series."""

    uuid: str
    schema_version: str
    seed: int
    kunde: str
    ersteller: str
    adresse: str
    static_limits: StaticLimits
    load_series: list
    created_at: str
    target_year: int
