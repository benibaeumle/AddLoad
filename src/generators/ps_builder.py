"""PSBuilder: hierarchical Power Summary aggregation via depth-first traversal."""

from __future__ import annotations

import numpy as np

from src.models.load_series import PSParameters, SLPParameters
from src.models.ps_node import PSNode, PSNodeType


class PSBuilder:
    """Builds a Power Summary load curve via depth-first post-order traversal."""

    @staticmethod
    def build(
        params: PSParameters,
        target_year: int,
        bdew_profiles: dict,
    ) -> np.ndarray:
        """Build the aggregated PS load curve from the node tree.

        Performs depth-first post-order traversal:
        - CONSUMER leaves call SLPGenerator.generate.
        - GROUP nodes sum children element-wise, then multiply by simultaneity_factor.

        Args:
            params: PSParameters containing the root PSNode.
            target_year: The target year for the time grid.
            bdew_profiles: BDEW profile lookup dict.

        Returns:
            numpy array of shape (35040,), dtype float64, all values >= 0.

        Raises:
            ValueError: if a CONSUMER has profile_type = None, or any
                        simultaneity_factor is <= 0.
        """
        return PSBuilder._traverse(params.root_node, target_year, bdew_profiles)

    @staticmethod
    def _traverse(node: PSNode, target_year: int, bdew_profiles: dict) -> np.ndarray:
        """Recursively compute the load array for a node."""
        from src.generators.slp_generator import SLPGenerator

        if node.node_type == PSNodeType.CONSUMER:
            if node.profile_type is None:
                raise ValueError(
                    f"Verbraucher '{node.name}' hat keinen Profiltyp (profile_type ist None)."
                )
            annual_kwh = node.annual_energy_kwh if node.annual_energy_kwh is not None else 0.0
            slp_params = SLPParameters(
                profile_type=node.profile_type,
                annual_energy_kwh=annual_kwh,
            )
            return SLPGenerator.generate(slp_params, target_year, bdew_profiles)

        if node.node_type == PSNodeType.GROUP:
            if node.simultaneity_factor <= 0:
                raise ValueError(
                    f"Gleichzeitigkeitsfaktor der Gruppe '{node.name}' muss > 0 sein, "
                    f"erhalten: {node.simultaneity_factor}"
                )
            if not node.children:
                return np.zeros(35040, dtype=float)

            child_arrays = [
                PSBuilder._traverse(child, target_year, bdew_profiles)
                for child in node.children
            ]
            combined = np.sum(child_arrays, axis=0)
            return combined * node.simultaneity_factor

        return np.zeros(35040, dtype=float)
