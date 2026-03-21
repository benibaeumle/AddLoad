"""Project page: create, select, edit metadata, import and export projects."""

from __future__ import annotations

import os

import streamlit as st

from src.services.project_service import ProjectService
from src.ui.components.error_display import show_errors

_PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "projects.json")


def render() -> None:
    """Render the project management page."""
    _ensure_session_state()

    st.header("Projektverwaltung")

    active_uuid = st.session_state.get("active_project_uuid")
    if active_uuid is None or active_uuid not in st.session_state["projects"]:
        st.info("Kein Projekt ausgewählt. Erstellen Sie ein neues Projekt in der Seitenleiste.")
        return

    project = st.session_state["projects"][active_uuid]

    # ---- Metadata form ----
    st.subheader("Projektdaten")
    kunde = st.text_input("Kunde", value=project.kunde, key="meta_kunde")
    ersteller = st.text_input("Ersteller", value=project.ersteller, key="meta_ersteller")
    adresse = st.text_input("Adresse", value=project.adresse, key="meta_adresse")
    target_year = st.number_input(
        "Zieljahr",
        min_value=2000,
        max_value=2100,
        value=project.target_year,
        step=1,
        key="meta_target_year",
    )

    if st.button("Speichern"):
        project.kunde = kunde
        project.ersteller = ersteller
        project.adresse = adresse
        project.target_year = int(target_year)
        ProjectService.save_all_to_disk(
            st.session_state["projects"],
            st.session_state.get("active_project_uuid"),
            _PROJECTS_FILE,
        )
        st.success("Projektdaten gespeichert.")

    st.divider()

    # ---- Export ----
    st.subheader("Projekt exportieren")
    errors = ProjectService.validate_for_export(project)
    if errors:
        show_errors(errors)
    else:
        try:
            json_str = ProjectService.to_json(project)
            filename = f"projekt_{project.uuid[:8]}.json"
            st.download_button(
                label="Projekt als JSON herunterladen",
                data=json_str.encode("utf-8"),
                file_name=filename,
                mime="application/json",
            )
        except ValueError as exc:
            st.error(str(exc))

    st.divider()

    # ---- Import ----
    st.subheader("Projekt laden")
    uploaded = st.file_uploader(
        "Projekt-JSON hochladen", type=["json"], key="project_upload"
    )
    if uploaded is not None:
        try:
            raw_json = uploaded.read().decode("utf-8")
            loaded_project, skipped = ProjectService.from_json(raw_json)
            st.session_state["projects"][loaded_project.uuid] = loaded_project
            ProjectService.switch_active(st.session_state, loaded_project.uuid)
            ProjectService.save_all_to_disk(
                st.session_state["projects"],
                st.session_state.get("active_project_uuid"),
                _PROJECTS_FILE,
            )
            if skipped:
                for name in skipped:
                    st.warning(f"Serie übersprungen: {name}")
            st.success(f"Projekt '{loaded_project.kunde}' erfolgreich geladen.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def _render_sidebar() -> None:
    """Render the project selector and new-project button in the sidebar."""
    projects: dict = st.session_state["projects"]

    if projects:
        options = list(projects.keys())
        labels = {uid: f"{p.kunde or uid[:8]} ({uid[:8]})" for uid, p in projects.items()}
        active_uuid = st.session_state.get("active_project_uuid")
        selected_idx = options.index(active_uuid) if active_uuid in options else 0
        selected_uuid = st.selectbox(
            "Aktives Projekt",
            options=options,
            index=selected_idx,
            format_func=lambda uid: labels[uid],
            key="project_selector",
        )
        if selected_uuid != st.session_state.get("active_project_uuid"):
            ProjectService.switch_active(st.session_state, selected_uuid)
            st.rerun()
    else:
        st.info("Noch keine Projekte vorhanden.")

    if st.button("Neues Projekt erstellen", key="btn_new_project"):
        new_project = ProjectService.create(kunde="", ersteller="", adresse="")
        st.session_state["projects"][new_project.uuid] = new_project
        ProjectService.switch_active(st.session_state, new_project.uuid)
        ProjectService.save_all_to_disk(
            st.session_state["projects"],
            st.session_state.get("active_project_uuid"),
            _PROJECTS_FILE,
        )
        st.rerun()


def _ensure_session_state() -> None:
    """Initialize session state keys if not present."""
    if "projects" not in st.session_state:
        st.session_state["projects"] = {}
    if "active_project_uuid" not in st.session_state:
        st.session_state["active_project_uuid"] = None
