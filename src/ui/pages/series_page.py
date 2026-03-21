"""Series page: add, edit, and delete load series of all types."""

from __future__ import annotations

import os
import uuid as _uuid

import streamlit as st

from src.models.load_series import (
    BESSParameters,
    BESSStrategy,
    CSVParameters,
    LoadSeries,
    MergeMode,
    PVAParameters,
    SLPParameters,
)
from src.models.project import SeriesType
from src.models.ps_node import PSNode, PSNodeType
from src.services.load_registry import LoadRegistry
from src.services.project_service import ProjectService
from src.ui.components.error_display import show_errors

_PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "projects.json")

_SLP_PROFILES = ["H0", "G0", "G1", "G2", "G3", "G4", "G5", "G6", "L0", "L1", "L2"]
_BESS_STRATEGIES = {
    "Peak Shaving": BESSStrategy.PEAK_SHAVING,
    "Eigenverbrauchsmaximierung": BESSStrategy.EIGENVERBRAUCH,
    "Arbitrage": BESSStrategy.ARBITRAGE,
}


def render() -> None:
    """Render the series management page."""
    _ensure_session_state()

    st.header("Lastgänge verwalten")

    active_uuid = st.session_state.get("active_project_uuid")
    if not active_uuid or active_uuid not in st.session_state.get("projects", {}):
        st.info("Kein Projekt ausgewählt.")
        return

    project = st.session_state["projects"][active_uuid]
    bdew_profiles = st.session_state.get("bdew_profiles", {})

    type_labels = {
        "SLP (BDEW Standardlastprofil)": SeriesType.SLP,
        "CSV/XLSX (Messdaten)": SeriesType.CSV,
        "PS (Power Summary)": SeriesType.PS,
        "PVA (Photovoltaik)": SeriesType.PVA,
        "BESS (Batteriespeicher)": SeriesType.BESS,
    }

    st.subheader("Neuen Lastgang hinzufügen")
    selected_type_label = st.selectbox(
        "Typ",
        options=list(type_labels.keys()),
        key="series_type_selector",
    )
    selected_type = type_labels[selected_type_label]

    if selected_type == SeriesType.SLP:
        _render_slp_form(project, bdew_profiles)
    elif selected_type == SeriesType.CSV:
        _render_csv_form(project, bdew_profiles)
    elif selected_type == SeriesType.PS:
        _render_ps_form(project, bdew_profiles)
    elif selected_type == SeriesType.PVA:
        _render_pva_form(project, bdew_profiles)
    elif selected_type == SeriesType.BESS:
        _render_bess_form(project, bdew_profiles)

    st.divider()
    _render_series_list(project, bdew_profiles)


# ------------------------------------------------------------------ #
# SLP form
# ------------------------------------------------------------------ #

def _render_slp_form(project, bdew_profiles: dict) -> None:
    """Render the SLP add form."""
    with st.form(key="slp_form"):
        st.markdown("**SLP – BDEW Standardlastprofil**")
        profile_type = st.selectbox("Profiltyp", options=_SLP_PROFILES, key="slp_profile")
        annual_energy = st.number_input(
            "Jahresenergie (kWh/a)", min_value=0.0, value=5000.0, step=100.0, key="slp_energy"
        )
        name = st.text_input("Name", value=f"SLP {profile_type}", key="slp_name")
        submitted = st.form_submit_button("Hinzufügen")

    if submitted:
        if annual_energy == 0:
            st.warning("Jahresenergie ist 0 kWh/a. Das Profil wird keine Leistung haben.")
        if not bdew_profiles:
            st.error("BDEW-Profile nicht geladen. Bitte starten Sie die Anwendung neu.")
            return
        try:
            from src.generators.slp_generator import SLPGenerator

            params = SLPParameters(
                profile_type=profile_type,
                annual_energy_kwh=annual_energy,
            )
            values = SLPGenerator.generate(params, project.target_year, bdew_profiles)
            series = LoadSeries(
                id=str(_uuid.uuid4()),
                name=name or f"SLP {profile_type} – {annual_energy:.0f} kWh/a",
                series_type=SeriesType.SLP,
                parameters=params,
                values=values.tolist(),
                is_active=True,
            )
            LoadRegistry.add(project, series)
            ProjectService.save_all_to_disk(
                st.session_state["projects"],
                st.session_state.get("active_project_uuid"),
                _PROJECTS_FILE,
            )
            st.success(f"Serie '{series.name}' hinzugefügt.")
            st.rerun()
        except Exception as exc:
            st.error(f"Fehler: {exc}")


# ------------------------------------------------------------------ #
# CSV/XLSX form
# ------------------------------------------------------------------ #

def _render_csv_form(project, bdew_profiles: dict) -> None:
    """Render the CSV/XLSX upload form."""
    st.markdown("**CSV/XLSX – Messdaten-Upload**")

    uploaded_files = st.file_uploader(
        "Dateien hochladen (.csv, .xlsx)",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        key="csv_uploader",
    )
    merge_mode_label = st.radio(
        "Mehrere Dateien",
        options=["Einzeln verarbeiten", "Gemeinsam verarbeiten (summieren)"],
        key="csv_merge_mode",
    )
    merge_mode = MergeMode.COMBINED if "summieren" in merge_mode_label else MergeMode.INDIVIDUAL

    if st.button("Hochladen und hinzufügen", key="csv_submit"):
        if not uploaded_files:
            st.error("Bitte wählen Sie mindestens eine Datei aus.")
            return

        from src.generators.csv_parser import parse_upload
        from src.normalizer import Normalizer

        arrays = []
        all_params = []
        errors = []
        detected_years = []

        for f in uploaded_files:
            file_bytes = f.read()
            if len(file_bytes) > 50 * 1024 * 1024:
                st.warning(f"Datei '{f.name}' ist größer als 50 MB. Verarbeitung kann dauern.")
            try:
                arr, params, detected_year = parse_upload(file_bytes, f.name, project.target_year)
                arrays.append(arr)
                all_params.append(params)
                detected_years.append(detected_year)
                if params.replaced_zeros > 0:
                    st.warning(
                        f"'{f.name}': {params.replaced_zeros} fehlende Werte wurden durch 0 ersetzt."
                    )
            except ValueError as exc:
                errors.append(str(exc))

        if errors:
            show_errors(errors)
            return

        if not arrays:
            st.error("Keine Daten konnten geladen werden.")
            return

        if detected_years:
            new_year = max(set(detected_years), key=detected_years.count)
            if new_year != project.target_year:
                project.target_year = new_year
                st.info(f"Zieljahr wurde automatisch auf {new_year} gesetzt.")

        if merge_mode == MergeMode.COMBINED and len(arrays) > 1:
            try:
                merged = Normalizer.merge_series(arrays, MergeMode.COMBINED)
                filenames = [p.source_filenames[0] for p in all_params]
                total_replaced = sum(p.replaced_zeros for p in all_params)
                first_col = all_params[0].column_name
                csv_params = CSVParameters(
                    source_filenames=filenames,
                    merge_mode=MergeMode.COMBINED,
                    column_name=first_col,
                    replaced_zeros=total_replaced,
                )
                series = LoadSeries(
                    id=str(_uuid.uuid4()),
                    name=f"CSV (kombiniert) – {len(filenames)} Dateien",
                    series_type=SeriesType.CSV,
                    parameters=csv_params,
                    values=merged.tolist(),
                    is_active=True,
                )
                LoadRegistry.add(project, series)
                ProjectService.save_all_to_disk(
                    st.session_state["projects"],
                    st.session_state.get("active_project_uuid"),
                    _PROJECTS_FILE,
                )
                st.success(f"Serie '{series.name}' hinzugefügt.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        else:
            for arr, params in zip(arrays, all_params):
                series = LoadSeries(
                    id=str(_uuid.uuid4()),
                    name=f"CSV – {params.source_filenames[0]}",
                    series_type=SeriesType.CSV,
                    parameters=params,
                    values=arr.tolist(),
                    is_active=True,
                )
                LoadRegistry.add(project, series)
            ProjectService.save_all_to_disk(
                st.session_state["projects"],
                st.session_state.get("active_project_uuid"),
                _PROJECTS_FILE,
            )
            st.success(f"{len(arrays)} Serie(n) hinzugefügt.")
            st.rerun()


# ------------------------------------------------------------------ #
# PS form
# ------------------------------------------------------------------ #

def _render_ps_form(project, bdew_profiles: dict) -> None:
    """Render the Power Summary tree builder form."""
    from src.models.load_series import PSParameters

    st.markdown("**PS – Power Summary (hierarchische Verbrauchsstruktur)**")

    if "ps_tree" not in st.session_state:
        root_id = str(_uuid.uuid4())
        st.session_state["ps_tree"] = {
            "root_id": root_id,
            "nodes": {
                root_id: {
                    "node_id": root_id,
                    "node_type": "GROUP",
                    "name": "Hauptgruppe",
                    "simultaneity_factor": 1.0,
                    "children": [],
                    "profile_type": None,
                    "annual_energy_kwh": None,
                    "parent_id": None,
                }
            },
        }

    tree = st.session_state["ps_tree"]
    nodes = tree["nodes"]
    root_id = tree["root_id"]

    _render_ps_node_editor(nodes, root_id)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("PS-Lastgang berechnen und hinzufügen", key="ps_submit"):
            if not bdew_profiles:
                st.error("BDEW-Profile nicht geladen.")
                return
            try:
                root_node = _build_ps_node(nodes, root_id)
                ps_params = PSParameters(root_node=root_node)
                from src.generators.ps_builder import PSBuilder
                values = PSBuilder.build(ps_params, project.target_year, bdew_profiles)
                series = LoadSeries(
                    id=str(_uuid.uuid4()),
                    name=f"PS – {root_node.name}",
                    series_type=SeriesType.PS,
                    parameters=ps_params,
                    values=values.tolist(),
                    is_active=True,
                )
                LoadRegistry.add(project, series)
                ProjectService.save_all_to_disk(
                    st.session_state["projects"],
                    st.session_state.get("active_project_uuid"),
                    _PROJECTS_FILE,
                )
                del st.session_state["ps_tree"]
                st.success(f"PS-Serie '{series.name}' hinzugefügt.")
                st.rerun()
            except Exception as exc:
                st.error(f"Fehler: {exc}")
    with col2:
        if st.button("Baum zurücksetzen", key="ps_reset"):
            if "ps_tree" in st.session_state:
                del st.session_state["ps_tree"]
            st.rerun()


def _render_ps_node_editor(nodes: dict, node_id: str, depth: int = 0) -> None:
    """Recursively render a PS node editor."""
    node = nodes[node_id]
    indent = "　" * depth

    with st.container():
        cols = st.columns([3, 1, 1])
        with cols[0]:
            node["name"] = st.text_input(
                f"{indent}Name",
                value=node["name"],
                key=f"ps_name_{node_id}",
                label_visibility="collapsed",
            )
        with cols[1]:
            type_label = st.selectbox(
                "Typ",
                options=["Gruppe", "Verbraucher"],
                index=0 if node["node_type"] == "GROUP" else 1,
                key=f"ps_type_{node_id}",
                label_visibility="collapsed",
            )
            node["node_type"] = "GROUP" if type_label == "Gruppe" else "CONSUMER"
        with cols[2]:
            if node["parent_id"] is not None:
                if st.button("✕", key=f"ps_del_{node_id}"):
                    _remove_ps_node(nodes, node_id)
                    st.rerun()

        if node["node_type"] == "GROUP":
            node["simultaneity_factor"] = st.number_input(
                f"{indent}Gleichzeitigkeitsfaktor",
                min_value=0.01,
                max_value=1.0,
                value=float(node.get("simultaneity_factor", 1.0)),
                step=0.05,
                key=f"ps_glf_{node_id}",
            )
            if node["simultaneity_factor"] > 1.0:
                st.warning("Gleichzeitigkeitsfaktor > 1 ist unüblich.")

            if st.button(f"{indent}+ Untergruppe hinzufügen", key=f"ps_addgrp_{node_id}"):
                new_id = str(_uuid.uuid4())
                nodes[new_id] = {
                    "node_id": new_id,
                    "node_type": "GROUP",
                    "name": "Untergruppe",
                    "simultaneity_factor": 1.0,
                    "children": [],
                    "profile_type": None,
                    "annual_energy_kwh": None,
                    "parent_id": node_id,
                }
                node["children"].append(new_id)
                st.rerun()

            if st.button(f"{indent}+ Verbraucher hinzufügen", key=f"ps_addcon_{node_id}"):
                new_id = str(_uuid.uuid4())
                nodes[new_id] = {
                    "node_id": new_id,
                    "node_type": "CONSUMER",
                    "name": "Verbraucher",
                    "simultaneity_factor": 1.0,
                    "children": [],
                    "profile_type": "H0",
                    "annual_energy_kwh": 3000.0,
                    "parent_id": node_id,
                }
                node["children"].append(new_id)
                st.rerun()

            for child_id in node["children"]:
                if child_id in nodes:
                    _render_ps_node_editor(nodes, child_id, depth + 1)

        else:
            node["profile_type"] = st.selectbox(
                f"{indent}Profiltyp",
                options=_SLP_PROFILES,
                index=_SLP_PROFILES.index(node.get("profile_type") or "H0"),
                key=f"ps_ptype_{node_id}",
            )
            node["annual_energy_kwh"] = st.number_input(
                f"{indent}Jahresenergie (kWh/a)",
                min_value=0.0,
                value=float(node.get("annual_energy_kwh") or 3000.0),
                step=500.0,
                key=f"ps_energy_{node_id}",
            )


def _remove_ps_node(nodes: dict, node_id: str) -> None:
    """Remove a node and all its descendants; update parent's children list."""
    node = nodes.get(node_id)
    if not node:
        return
    parent_id = node.get("parent_id")
    if parent_id and parent_id in nodes:
        nodes[parent_id]["children"] = [
            c for c in nodes[parent_id]["children"] if c != node_id
        ]
    for child_id in list(node.get("children", [])):
        _remove_ps_node(nodes, child_id)
    nodes.pop(node_id, None)


def _build_ps_node(nodes: dict, node_id: str) -> PSNode:
    """Recursively build a PSNode tree from the session-state dict."""
    node = nodes[node_id]
    children = [_build_ps_node(nodes, cid) for cid in node["children"] if cid in nodes]
    return PSNode(
        node_id=node["node_id"],
        node_type=PSNodeType(node["node_type"]),
        name=node["name"],
        simultaneity_factor=float(node.get("simultaneity_factor", 1.0)),
        children=children,
        profile_type=node.get("profile_type"),
        annual_energy_kwh=node.get("annual_energy_kwh"),
    )


# ------------------------------------------------------------------ #
# PVA form
# ------------------------------------------------------------------ #

def _render_pva_form(project, bdew_profiles: dict) -> None:
    """Render the PVA add form."""
    with st.form(key="pva_form"):
        st.markdown("**PVA – Photovoltaikanlage**")
        peak_power = st.number_input(
            "Spitzenleistung (kWp)", min_value=0.0, value=10.0, step=1.0, key="pva_kwp"
        )
        azimuth = st.slider(
            "Ausrichtung/Azimut (°, 0=N, 90=E, 180=S, 270=W)",
            min_value=0,
            max_value=360,
            value=180,
            key="pva_azimuth",
        )
        tilt = st.slider(
            "Neigungswinkel (°, 0=horizontal, 90=vertikal)",
            min_value=0,
            max_value=90,
            value=30,
            key="pva_tilt",
        )
        climate_zone = st.selectbox(
            "Klimazone", options=["central_europe"], key="pva_climate"
        )
        name = st.text_input("Name", value=f"PVA {peak_power:.0f} kWp", key="pva_name")
        submitted = st.form_submit_button("Hinzufügen")

    if submitted:
        if peak_power == 0:
            st.warning("Spitzenleistung ist 0 kWp.")
        try:
            from src.generators.pv_generator import PVGenerator

            params = PVAParameters(
                peak_power_kwp=peak_power,
                azimuth_deg=float(azimuth),
                tilt_deg=float(tilt),
                climate_zone=climate_zone,
            )
            values = PVGenerator.generate(params, project.target_year, project.seed)
            series = LoadSeries(
                id=str(_uuid.uuid4()),
                name=name or f"PVA {peak_power:.0f} kWp",
                series_type=SeriesType.PVA,
                parameters=params,
                values=values.tolist(),
                is_active=True,
            )
            LoadRegistry.add(project, series)
            ProjectService.save_all_to_disk(
                st.session_state["projects"],
                st.session_state.get("active_project_uuid"),
                _PROJECTS_FILE,
            )
            st.success(f"PVA-Serie '{series.name}' hinzugefügt.")
            st.rerun()
        except Exception as exc:
            st.error(f"Fehler: {exc}")


# ------------------------------------------------------------------ #
# BESS form
# ------------------------------------------------------------------ #

def _render_bess_form(project, bdew_profiles: dict) -> None:
    """Render the BESS add form."""
    non_bess_active = [
        s for s in project.load_series
        if s.is_active and s.series_type != SeriesType.BESS
    ]
    if not non_bess_active:
        st.warning(
            "Das Projekt enthält noch keine aktiven Lastgänge (SLP, CSV, PS, PVA). "
            "Das BESS-Profil wird null sein, bis andere Serien vorhanden sind."
        )

    with st.form(key="bess_form"):
        st.markdown("**BESS – Batteriespeichersystem**")
        capacity = st.number_input(
            "Kapazität (kWh)", min_value=0.1, value=100.0, step=10.0, key="bess_cap"
        )
        max_charge = st.number_input(
            "Max. Ladeleistung (kW)", min_value=0.1, value=50.0, step=5.0, key="bess_charge"
        )
        max_discharge = st.number_input(
            "Max. Entladeleistung (kW)", min_value=0.1, value=50.0, step=5.0, key="bess_discharge"
        )
        efficiency = st.number_input(
            "Wirkungsgrad (%)", min_value=1.0, max_value=100.0, value=90.0, step=1.0, key="bess_eff"
        )
        strategy_label = st.selectbox(
            "Strategie",
            options=list(_BESS_STRATEGIES.keys()),
            key="bess_strategy",
        )
        threshold_str = st.text_input(
            "Peak-Shaving-Schwelle (kW, leer = automatisch 90. Perzentil)",
            value="",
            key="bess_threshold",
        )
        name = st.text_input("Name", value="BESS", key="bess_name")
        submitted = st.form_submit_button("Hinzufügen")

    if submitted:
        try:
            threshold: float | None = None
            if threshold_str.strip():
                threshold = float(threshold_str.strip())

            from src.generators.bess_simulator import BESSSimulator
            import numpy as np

            params = BESSParameters(
                capacity_kwh=capacity,
                max_charge_power_kw=max_charge,
                max_discharge_power_kw=max_discharge,
                efficiency_pct=efficiency,
                strategy=_BESS_STRATEGIES[strategy_label],
                peak_shaving_threshold_kw=threshold,
            )

            net_load = np.zeros(35040, dtype=float)
            for s in non_bess_active:
                net_load += np.array(s.values, dtype=float)

            values = BESSSimulator.simulate(params, net_load)
            series = LoadSeries(
                id=str(_uuid.uuid4()),
                name=name or f"BESS {capacity:.0f} kWh",
                series_type=SeriesType.BESS,
                parameters=params,
                values=values.tolist(),
                is_active=True,
            )
            LoadRegistry.add(project, series)
            ProjectService.save_all_to_disk(
                st.session_state["projects"],
                st.session_state.get("active_project_uuid"),
                _PROJECTS_FILE,
            )
            st.success(f"BESS-Serie '{series.name}' hinzugefügt.")
            st.rerun()
        except Exception as exc:
            st.error(f"Fehler: {exc}")


# ------------------------------------------------------------------ #
# Series list
# ------------------------------------------------------------------ #

def _render_series_list(project, bdew_profiles: dict) -> None:
    """Render the list of existing series with toggle and delete controls."""
    st.subheader("Vorhandene Lastgänge")

    if not project.load_series:
        st.info("Noch keine Lastgänge vorhanden.")
        return

    for series in project.load_series:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(
                    f"**{series.name}** "
                    f"<span style='color:gray;font-size:0.85em;'>{series.series_type.value}</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                peak = max(series.values) if series.values else 0.0
                st.caption(f"Peak: {peak:.2f} kW")
            with col3:
                new_active = st.checkbox(
                    "Aktiv",
                    value=series.is_active,
                    key=f"active_{series.id}",
                )
                if new_active != series.is_active:
                    LoadRegistry.set_active(project, series.id, new_active)
                    ProjectService.save_all_to_disk(
                        st.session_state["projects"],
                        st.session_state.get("active_project_uuid"),
                        _PROJECTS_FILE,
                    )
                    st.rerun()
            with col4:
                if st.button("Löschen", key=f"del_{series.id}"):
                    LoadRegistry.remove(project, series.id)
                    ProjectService.save_all_to_disk(
                        st.session_state["projects"],
                        st.session_state.get("active_project_uuid"),
                        _PROJECTS_FILE,
                    )
                    st.success(f"Serie '{series.name}' gelöscht.")
                    st.rerun()


def _ensure_session_state() -> None:
    """Initialize session state keys if not present."""
    if "projects" not in st.session_state:
        st.session_state["projects"] = {}
    if "active_project_uuid" not in st.session_state:
        st.session_state["active_project_uuid"] = None
