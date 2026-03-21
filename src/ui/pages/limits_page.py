"""Limits page: configure static power limit values for chart display."""

from __future__ import annotations

import os

import streamlit as st

from src.services.project_service import ProjectService

_PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "projects.json")


def render() -> None:
    """Render the static limits configuration page."""
    st.header("Statische Grenzwerte")

    active_uuid = st.session_state.get("active_project_uuid")
    if not active_uuid or active_uuid not in st.session_state.get("projects", {}):
        st.info("Kein Projekt ausgewählt.")
        return

    project = st.session_state["projects"][active_uuid]
    limits = project.static_limits

    st.markdown(
        "Geben Sie optionale Leistungsgrenzwerte ein. Diese werden als gestrichelte "
        "Linien im Chart angezeigt. Lassen Sie ein Feld leer, um den Grenzwert "
        "auszublenden."
    )

    sicherung_str = st.text_input(
        "Sicherung (kW)",
        value=str(limits.sicherung_kw) if limits.sicherung_kw is not None else "",
        key="limits_sicherung",
    )
    hausanschluss_str = st.text_input(
        "Hausanschluss (kW)",
        value=str(limits.hausanschluss_kw) if limits.hausanschluss_kw is not None else "",
        key="limits_hausanschluss",
    )
    trafo_str = st.text_input(
        "Trafo (kW)",
        value=str(limits.trafo_kw) if limits.trafo_kw is not None else "",
        key="limits_trafo",
    )

    if st.button("Grenzwerte speichern"):
        limits.sicherung_kw = _parse_optional_float(sicherung_str, "Sicherung")
        limits.hausanschluss_kw = _parse_optional_float(hausanschluss_str, "Hausanschluss")
        limits.trafo_kw = _parse_optional_float(trafo_str, "Trafo")
        ProjectService.save_all_to_disk(
            st.session_state["projects"],
            st.session_state.get("active_project_uuid"),
            _PROJECTS_FILE,
        )
        st.success("Grenzwerte gespeichert. Die Änderungen sind im Chart sichtbar.")


def _parse_optional_float(value: str, field_name: str) -> float | None:
    """Parse a string to float or None; shows st.error on invalid input."""
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        st.error(f"Ungültiger Wert für '{field_name}': '{stripped}'. Bitte eine Zahl eingeben.")
        return None
