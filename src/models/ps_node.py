"""Data models for Power Summary node tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PSNodeType(str, Enum):
    """Type of a node in the Power Summary tree."""

    GROUP = "GROUP"
    CONSUMER = "CONSUMER"


@dataclass
class PSNode:
    """A node in the Power Summary hierarchy (either a group or a consumer leaf)."""

    node_id: str
    node_type: PSNodeType
    name: str
    simultaneity_factor: float = 1.0
    children: list[PSNode] = field(default_factory=list)
    profile_type: str | None = None
    annual_energy_kwh: float | None = None
