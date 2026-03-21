"""Aggregator: computes per-category sums and TOTAL net curve from a project."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.models.project import Project, SeriesType
from src.normalizer import Normalizer


@dataclass
class AggregationResult:
    """Result of aggregating all active load series in a project."""

    df: pd.DataFrame
    category_sums: dict
    total: np.ndarray
    peak_kw: float
    valley_kw: float


class Aggregator:
    """Computes category sums and TOTAL net curve from a project's active series."""

    @staticmethod
    def compute(project: Project) -> AggregationResult:
        """Compute per-category sums and TOTAL from all active series.

        Args:
            project: The project containing load_series entries.

        Returns:
            AggregationResult with DataFrame, category sums, total curve,
            peak and valley values.

        Raises:
            ValueError: if any active series values array has wrong shape.
        """
        canonical = Normalizer.canonical_index(project.target_year)
        n_steps = 35040

        active_series = [s for s in project.load_series if s.is_active]

        categories = [
            SeriesType.CSV,
            SeriesType.SLP,
            SeriesType.PS,
            SeriesType.PVA,
            SeriesType.BESS,
        ]
        cat_arrays: dict[SeriesType, np.ndarray] = {
            cat: np.zeros(n_steps, dtype=float) for cat in categories
        }

        individual_cols: dict[str, np.ndarray] = {}

        for s in active_series:
            arr = np.array(s.values, dtype=float)
            if arr.shape != (n_steps,):
                raise ValueError(
                    f"Serie '{s.name}' hat die falsche Form {arr.shape}. "
                    f"Erwartet wird ({n_steps},)."
                )
            individual_cols[s.name] = arr
            cat_arrays[s.series_type] += arr

        total = sum(cat_arrays[c] for c in categories)
        total = np.asarray(total, dtype=float)

        data: dict[str, np.ndarray] = {}
        data.update(individual_cols)
        data["CSV_SUM"] = cat_arrays[SeriesType.CSV]
        data["SLP_SUM"] = cat_arrays[SeriesType.SLP]
        data["PS_SUM"] = cat_arrays[SeriesType.PS]
        data["PVA_SUM"] = cat_arrays[SeriesType.PVA]
        data["BESS_SUM"] = cat_arrays[SeriesType.BESS]
        data["TOTAL"] = total

        df = pd.DataFrame(data, index=canonical)

        category_sums = {
            "CSV_SUM": cat_arrays[SeriesType.CSV],
            "SLP_SUM": cat_arrays[SeriesType.SLP],
            "PS_SUM": cat_arrays[SeriesType.PS],
            "PVA_SUM": cat_arrays[SeriesType.PVA],
            "BESS_SUM": cat_arrays[SeriesType.BESS],
        }

        peak_kw = float(total.max()) if len(total) > 0 else 0.0
        valley_kw = float(total.min()) if len(total) > 0 else 0.0

        return AggregationResult(
            df=df,
            category_sums=category_sums,
            total=total,
            peak_kw=peak_kw,
            valley_kw=valley_kw,
        )
