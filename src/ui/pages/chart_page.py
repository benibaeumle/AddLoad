"""Chart page: interactive Plotly P(t) chart with category toggles."""

from __future__ import annotations

import streamlit as st

from src.aggregator import Aggregator
from src.plot_engine import PlotEngine


def render() -> None:
    """Render the annual load curve chart page."""
    st.header("Lastgang-Chart")

    active_uuid = st.session_state.get("active_project_uuid")
    if not active_uuid or active_uuid not in st.session_state.get("projects", {}):
        st.info("Kein Projekt ausgewählt.")
        return

    project = st.session_state["projects"][active_uuid]

    result = Aggregator.compute(project)

    if "chart_visible" not in st.session_state:
        st.session_state["chart_visible"] = {}

    visible = st.session_state["chart_visible"]

    df_cols = list(result.df.columns)
    agg_cols = {"CSV_SUM", "SLP_SUM", "PS_SUM", "PVA_SUM", "BESS_SUM", "TOTAL"}
    individual_cols = [c for c in df_cols if c not in agg_cols]

    if individual_cols:
        st.subheader("Einzelne Serien anzeigen")
        cols = st.columns(min(4, len(individual_cols)))
        for i, col_name in enumerate(individual_cols):
            with cols[i % len(cols)]:
                current = visible.get(col_name, False)
                new_val = st.checkbox(col_name, value=current, key=f"vis_{col_name}")
                visible[col_name] = new_val

    fig = PlotEngine.build_figure(result, project.static_limits, visible)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Peak: {result.peak_kw:.2f} kW | Valley: {result.valley_kw:.2f} kW | "
        f"Aktive Serien: {sum(1 for s in project.load_series if s.is_active)}"
    )
