"""LoadRegistry: CRUD for LoadSeries within a project with reactivity."""

from __future__ import annotations

import numpy as np

from src.models.load_series import BESSParameters, LoadSeries
from src.models.project import Project, SeriesType


class LoadRegistry:
    """Central CRUD store for LoadSeries; triggers BESS recomputation on change."""

    @staticmethod
    def add(project: Project, series: LoadSeries) -> Project:
        """Append a new LoadSeries to the project and recompute BESS.

        Args:
            project: The project to add the series to.
            series: A fully-resolved LoadSeries (values already computed).

        Returns:
            The modified project.

        Raises:
            ValueError: if series.id already exists in the project.
        """
        existing_ids = {s.id for s in project.load_series}
        if series.id in existing_ids:
            raise ValueError(
                f"Eine Serie mit der ID '{series.id}' existiert bereits im Projekt."
            )
        project.load_series.append(series)
        LoadRegistry.recompute_bess(project)
        return project

    @staticmethod
    def update(
        project: Project,
        series_id: str,
        new_parameters: object,
        bdew_profiles: dict | None = None,
    ) -> Project:
        """Replace parameters of an existing series and recompute its values.

        Args:
            project: The project containing the series.
            series_id: ID of the series to update.
            new_parameters: New parameter dataclass instance.
            bdew_profiles: BDEW profile dict required for SLP/PS series.

        Returns:
            The modified project.

        Raises:
            KeyError: if series_id not found.
            ValueError: if new_parameters fail validation.
        """
        series = LoadRegistry._find(project, series_id)
        series.parameters = new_parameters
        series.values = LoadRegistry._recompute_series(series, project, bdew_profiles)

        if series.series_type != SeriesType.BESS:
            LoadRegistry.recompute_bess(project)
        return project

    @staticmethod
    def remove(project: Project, series_id: str) -> Project:
        """Remove a LoadSeries from the project and recompute BESS.

        Args:
            project: The project to remove from.
            series_id: ID of the series to remove.

        Returns:
            The modified project.

        Raises:
            KeyError: if series_id not found.
        """
        LoadRegistry._find(project, series_id)
        project.load_series = [s for s in project.load_series if s.id != series_id]
        LoadRegistry.recompute_bess(project)
        return project

    @staticmethod
    def set_active(project: Project, series_id: str, active: bool) -> Project:
        """Toggle the is_active flag of a series and recompute BESS.

        Args:
            project: The project containing the series.
            series_id: ID of the series to toggle.
            active: New active state.

        Returns:
            The modified project.

        Raises:
            KeyError: if series_id not found.
        """
        series = LoadRegistry._find(project, series_id)
        series.is_active = active
        LoadRegistry.recompute_bess(project)
        return project

    @staticmethod
    def recompute_bess(project: Project) -> Project:
        """Recompute all BESS series using the current net load.

        Net load = element-wise sum of all non-BESS active series values.

        Returns:
            The modified project.
        """
        from src.generators.bess_simulator import BESSSimulator

        non_bess_active = [
            s
            for s in project.load_series
            if s.is_active and s.series_type != SeriesType.BESS
        ]

        net_load = np.zeros(35040, dtype=float)
        for s in non_bess_active:
            net_load += np.array(s.values, dtype=float)

        bess_series = [
            s for s in project.load_series if s.series_type == SeriesType.BESS
        ]
        for bess in bess_series:
            bess.values = BESSSimulator.simulate(bess.parameters, net_load).tolist()

        return project

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _find(project: Project, series_id: str) -> LoadSeries:
        """Find a series by ID or raise KeyError."""
        for s in project.load_series:
            if s.id == series_id:
                return s
        raise KeyError(f"Serie mit ID '{series_id}' nicht gefunden.")

    @staticmethod
    def _recompute_series(
        series: LoadSeries,
        project: Project,
        bdew_profiles: dict | None,
    ) -> list[float]:
        """Recompute values for a series based on its type and parameters."""
        from src.generators.bess_simulator import BESSSimulator
        from src.generators.csv_parser import parse_upload
        from src.generators.ps_builder import PSBuilder
        from src.generators.pv_generator import PVGenerator
        from src.generators.slp_generator import SLPGenerator

        if series.series_type == SeriesType.SLP:
            return SLPGenerator.generate(
                series.parameters, project.target_year, bdew_profiles or {}
            ).tolist()
        elif series.series_type == SeriesType.PS:
            return PSBuilder.build(
                series.parameters, project.target_year, bdew_profiles or {}
            ).tolist()
        elif series.series_type == SeriesType.PVA:
            return PVGenerator.generate(
                series.parameters, project.target_year, project.seed
            ).tolist()
        elif series.series_type == SeriesType.BESS:
            non_bess = [
                s
                for s in project.load_series
                if s.is_active and s.series_type != SeriesType.BESS
            ]
            net_load = np.zeros(35040, dtype=float)
            for s in non_bess:
                net_load += np.array(s.values, dtype=float)
            return BESSSimulator.simulate(series.parameters, net_load).tolist()
        return series.values
