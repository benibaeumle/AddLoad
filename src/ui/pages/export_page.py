"""Export page: CSV and JSON export triggers."""

from __future__ import annotations

import streamlit as st

from src.aggregator import Aggregator
from src.export_engine import ExportEngine
from src.services.project_service import ProjectService
from src.ui.components.error_display import show_errors


def render() -> None:
    """Render the export page with CSV and JSON download buttons."""
    st.header("Daten exportieren")

    active_uuid = st.session_state.get("active_project_uuid")
    if not active_uuid or active_uuid not in st.session_state.get("projects", {}):
        st.info("Kein Projekt ausgewählt.")
        return

    project = st.session_state["projects"][active_uuid]

    errors = ProjectService.validate_for_export(project)
    if errors:
        show_errors(errors)
        st.warning("Bitte füllen Sie alle Pflichtfelder aus, bevor Sie exportieren.")
        return

    result = Aggregator.compute(project)

    st.subheader("Zeitreihendaten als CSV")
    try:
        csv_bytes = ExportEngine.to_csv_bytes(result)
        csv_filename = f"slp_export_{project.uuid[:8]}_{project.target_year}.csv"
        st.download_button(
            label="CSV herunterladen",
            data=csv_bytes,
            file_name=csv_filename,
            mime="text/csv",
        )
        st.caption(f"Format: UTF-8 mit BOM, Trennzeichen ';', {len(result.df)} Zeilen")
    except Exception as exc:
        st.error(f"Fehler beim Erstellen der CSV-Datei: {exc}")

    st.divider()

    st.subheader("Projektdefinition als JSON")
    try:
        json_bytes = ExportEngine.to_json_bytes(project)
        json_filename = f"projekt_{project.uuid[:8]}.json"
        st.download_button(
            label="JSON herunterladen",
            data=json_bytes,
            file_name=json_filename,
            mime="application/json",
        )
        st.caption(f"Schema-Version: {project.schema_version}")
    except ValueError as exc:
        st.error(str(exc))
