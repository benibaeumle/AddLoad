"""Streamlit entry point: load BDEW profiles and route to pages."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src.services.project_service import ProjectService
from src.ui.pages import chart_page, export_page, limits_page, project_page, series_page

st.set_page_config(page_title="SLP Lastgang-Verwaltung", layout="wide")

_BDEW_DIR = os.path.join(os.path.dirname(__file__), "data", "bdew")
_PROFILES = ["H0", "G0", "G1", "G2", "G3", "G4", "G5", "G6", "L0", "L1", "L2"]
PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "projects.json")


@st.cache_data
def _load_bdew_profiles() -> dict[str, pd.DataFrame]:
    """Load all BDEW normalised profiles from CSV files into a dict."""
    profiles: dict[str, pd.DataFrame] = {}
    for name in _PROFILES:
        path = os.path.join(_BDEW_DIR, f"{name}.csv")
        if os.path.exists(path):
            profiles[name] = pd.read_csv(path)
    return profiles


def _init_session_state() -> None:
    """Initialize required session state keys on first run."""
    if "projects" not in st.session_state:
        projects, active_uuid, _ = ProjectService.load_all_from_disk(PROJECTS_FILE)
        st.session_state["projects"] = projects
        st.session_state["active_project_uuid"] = active_uuid
    if "active_project_uuid" not in st.session_state:
        st.session_state["active_project_uuid"] = None
    if "chart_visible" not in st.session_state:
        st.session_state["chart_visible"] = {}
    if "bdew_profiles" not in st.session_state:
        st.session_state["bdew_profiles"] = _load_bdew_profiles()


_init_session_state()

_PAGES = {
    "Projekt": project_page,
    "Lastgänge": series_page,
    "Grenzwerte": limits_page,
    "Chart": chart_page,
    "Export": export_page,
}

with st.sidebar:
    st.title("SLP Lastgang-Verwaltung")
    st.divider()
    selected_page = st.radio(
        "Navigation",
        options=list(_PAGES.keys()),
        key="nav_page",
        label_visibility="collapsed",
    )
    st.divider()
    project_page._render_sidebar()

_PAGES[selected_page].render()
