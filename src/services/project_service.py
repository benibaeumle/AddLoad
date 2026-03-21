"""ProjectService: create, validate, serialize, and deserialize projects."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from src.models.load_series import (
    BESSParameters,
    BESSStrategy,
    CSVParameters,
    LoadSeries,
    MergeMode,
    PVAParameters,
    SLPParameters,
)
from src.models.project import Project, SeriesType, StaticLimits
from src.models.ps_node import PSNode, PSNodeType

SCHEMA_VERSION = "1.0"


class ProjectService:
    """Service for creating, validating, and persisting projects."""

    @staticmethod
    def create(
        kunde: str,
        ersteller: str,
        adresse: str,
        seed: int | None = None,
    ) -> Project:
        """Create a new project with a UUID4 and target_year = current_year - 2.

        Args:
            kunde: Client name.
            ersteller: Creator name.
            adresse: Project address.
            seed: Optional integer seed; generated via secrets.randbelow if None.

        Returns:
            A new Project instance.
        """
        import uuid as _uuid

        if seed is None:
            seed = secrets.randbelow(2**32)

        now = datetime.now(timezone.utc)
        target_year = now.year - 2

        return Project(
            uuid=str(_uuid.uuid4()),
            schema_version=SCHEMA_VERSION,
            seed=seed,
            kunde=kunde,
            ersteller=ersteller,
            adresse=adresse,
            static_limits=StaticLimits(),
            load_series=[],
            created_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            target_year=target_year,
        )

    @staticmethod
    def validate_for_export(project: Project) -> list[str]:
        """Validate a project for export, returning German error strings.

        Args:
            project: The project to validate.

        Returns:
            A list of German error message strings. Empty list means valid.
        """
        errors: list[str] = []
        if not project.kunde or not project.kunde.strip():
            errors.append("Fehler: Das Feld 'Kunde' darf nicht leer sein.")
        if not project.ersteller or not project.ersteller.strip():
            errors.append("Fehler: Das Feld 'Ersteller' darf nicht leer sein.")
        if not project.adresse or not project.adresse.strip():
            errors.append("Fehler: Das Feld 'Adresse' darf nicht leer sein.")
        return errors

    @staticmethod
    def to_json(project: Project) -> str:
        """Serialize a project to a JSON string (schema v1.0).

        Args:
            project: The project to serialize.

        Returns:
            JSON string representation of the project.

        Raises:
            ValueError: if the project fails validation.
        """
        errors = ProjectService.validate_for_export(project)
        if errors:
            raise ValueError("\n".join(errors))

        data = ProjectService._project_to_dict(project)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def from_json(raw_json: str) -> tuple[Project, list[str]]:
        """Deserialize a project from a JSON string.

        Args:
            raw_json: JSON string to parse.

        Returns:
            Tuple of (Project, skipped_series_names). Unknown series_type
            values are skipped and their names recorded in the second element.

        Raises:
            ValueError: on malformed JSON or unknown schema_version.
        """
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ungültiges JSON-Format: {exc}") from exc

        version = data.get("schema_version", "1.0")
        if version != "1.0":
            raise ValueError(f"Unbekannte Schema-Version: {version}")

        return ProjectService._load_v1(data)

    @staticmethod
    def switch_active(session_state: dict, uuid: str) -> None:
        """Switch the active project in Streamlit session state.

        Args:
            session_state: The st.session_state dict.
            uuid: UUID of the project to activate.
        """
        session_state["active_project_uuid"] = uuid

    @staticmethod
    def save_all_to_disk(projects: dict, active_uuid: str | None, path: str) -> None:
        """Persist all projects and the active UUID to a JSON file on disk.

        Args:
            projects: Dict mapping UUID -> Project.
            active_uuid: Currently active project UUID or None.
            path: Absolute path to the target JSON file.
        """
        import os

        data = {
            "active_project_uuid": active_uuid,
            "projects": {
                uid: ProjectService._project_to_dict(p) for uid, p in projects.items()
            },
        }
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    @staticmethod
    def load_all_from_disk(path: str) -> tuple[dict, str | None, list[str]]:
        """Load all projects from a JSON file written by save_all_to_disk.

        Args:
            path: Absolute path to the JSON file.

        Returns:
            Tuple of (projects_dict, active_uuid, skipped_names).
            projects_dict maps UUID -> Project.
            Returns ({}, None, []) if the file does not exist or is corrupt.
        """
        import os

        if not os.path.exists(path):
            return {}, None, []

        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}, None, []

        projects: dict = {}
        all_skipped: list[str] = []
        for uid, p_data in data.get("projects", {}).items():
            try:
                version = p_data.get("schema_version", "1.0")
                if version != "1.0":
                    all_skipped.append(uid)
                    continue
                project, skipped = ProjectService._load_v1(p_data)
                projects[uid] = project
                all_skipped.extend(skipped)
            except (KeyError, ValueError):
                all_skipped.append(uid)

        active_uuid = data.get("active_project_uuid")
        if active_uuid not in projects:
            active_uuid = next(iter(projects), None)

        return projects, active_uuid, all_skipped

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _project_to_dict(project: Project) -> dict:
        """Convert a Project to a JSON-serialisable dict."""
        return {
            "schema_version": project.schema_version,
            "uuid": project.uuid,
            "seed": project.seed,
            "kunde": project.kunde,
            "ersteller": project.ersteller,
            "adresse": project.adresse,
            "created_at": project.created_at,
            "target_year": project.target_year,
            "static_limits": {
                "sicherung_kw": project.static_limits.sicherung_kw,
                "hausanschluss_kw": project.static_limits.hausanschluss_kw,
                "trafo_kw": project.static_limits.trafo_kw,
            },
            "load_series": [
                ProjectService._series_to_dict(s) for s in project.load_series
            ],
        }

    @staticmethod
    def _series_to_dict(series: LoadSeries) -> dict:
        """Convert a LoadSeries to a JSON-serialisable dict."""
        params = ProjectService._params_to_dict(series.parameters, series.series_type)
        return {
            "id": series.id,
            "name": series.name,
            "series_type": series.series_type.value,
            "is_active": series.is_active,
            "parameters": params,
            "values": [float(v) for v in series.values],
        }

    @staticmethod
    def _params_to_dict(params: object, series_type: SeriesType) -> dict:
        """Convert parameters dataclass to dict."""
        if series_type == SeriesType.SLP:
            return {
                "profile_type": params.profile_type,
                "annual_energy_kwh": params.annual_energy_kwh,
            }
        elif series_type == SeriesType.CSV:
            return {
                "source_filenames": params.source_filenames,
                "merge_mode": params.merge_mode.value,
                "column_name": params.column_name,
                "replaced_zeros": params.replaced_zeros,
            }
        elif series_type == SeriesType.PS:
            return {
                "root_node": ProjectService._ps_node_to_dict(params.root_node),
            }
        elif series_type == SeriesType.PVA:
            return {
                "peak_power_kwp": params.peak_power_kwp,
                "azimuth_deg": params.azimuth_deg,
                "tilt_deg": params.tilt_deg,
                "climate_zone": params.climate_zone,
            }
        elif series_type == SeriesType.BESS:
            return {
                "capacity_kwh": params.capacity_kwh,
                "max_charge_power_kw": params.max_charge_power_kw,
                "max_discharge_power_kw": params.max_discharge_power_kw,
                "efficiency_pct": params.efficiency_pct,
                "strategy": params.strategy.value,
                "peak_shaving_threshold_kw": params.peak_shaving_threshold_kw,
            }
        return {}

    @staticmethod
    def _ps_node_to_dict(node: PSNode) -> dict:
        """Convert a PSNode tree to a dict."""
        return {
            "node_id": node.node_id,
            "node_type": node.node_type.value,
            "name": node.name,
            "simultaneity_factor": node.simultaneity_factor,
            "children": [ProjectService._ps_node_to_dict(c) for c in node.children],
            "profile_type": node.profile_type,
            "annual_energy_kwh": node.annual_energy_kwh,
        }

    @staticmethod
    def _load_v1(data: dict) -> tuple[Project, list[str]]:
        """Load a schema v1.0 project dict."""
        limits_data = data.get("static_limits", {})
        static_limits = StaticLimits(
            sicherung_kw=limits_data.get("sicherung_kw"),
            hausanschluss_kw=limits_data.get("hausanschluss_kw"),
            trafo_kw=limits_data.get("trafo_kw"),
        )

        load_series = []
        skipped: list[str] = []

        for s_data in data.get("load_series", []):
            try:
                series = ProjectService._load_series_v1(s_data)
                load_series.append(series)
            except (KeyError, ValueError) as exc:
                name = s_data.get("name", s_data.get("id", "unbekannt"))
                skipped.append(f"{name}: {exc}")

        project = Project(
            uuid=data["uuid"],
            schema_version=data.get("schema_version", "1.0"),
            seed=data.get("seed", 0),
            kunde=data.get("kunde", ""),
            ersteller=data.get("ersteller", ""),
            adresse=data.get("adresse", ""),
            static_limits=static_limits,
            load_series=load_series,
            created_at=data.get("created_at", ""),
            target_year=data.get("target_year", datetime.now(timezone.utc).year - 2),
        )
        return project, skipped

    @staticmethod
    def _load_series_v1(s_data: dict) -> LoadSeries:
        """Deserialize a single LoadSeries from a v1 dict."""
        from src.models.load_series import PSParameters

        series_type_str = s_data.get("series_type", "")
        try:
            series_type = SeriesType(series_type_str)
        except ValueError:
            raise ValueError(f"Unbekannter series_type: '{series_type_str}'")

        params_data = s_data.get("parameters", {})
        params = ProjectService._load_params_v1(params_data, series_type)

        return LoadSeries(
            id=s_data["id"],
            name=s_data.get("name", ""),
            series_type=series_type,
            parameters=params,
            values=s_data.get("values", []),
            is_active=s_data.get("is_active", True),
        )

    @staticmethod
    def _load_params_v1(params_data: dict, series_type: SeriesType) -> object:
        """Deserialize parameters from a v1 dict."""
        from src.models.load_series import PSParameters

        if series_type == SeriesType.SLP:
            return SLPParameters(
                profile_type=params_data["profile_type"],
                annual_energy_kwh=float(params_data["annual_energy_kwh"]),
            )
        elif series_type == SeriesType.CSV:
            return CSVParameters(
                source_filenames=params_data.get("source_filenames", []),
                merge_mode=MergeMode(params_data.get("merge_mode", "INDIVIDUAL")),
                column_name=params_data.get("column_name", ""),
                replaced_zeros=int(params_data.get("replaced_zeros", 0)),
            )
        elif series_type == SeriesType.PS:
            root_node = ProjectService._load_ps_node(params_data["root_node"])
            return PSParameters(root_node=root_node)
        elif series_type == SeriesType.PVA:
            return PVAParameters(
                peak_power_kwp=float(params_data["peak_power_kwp"]),
                azimuth_deg=float(params_data["azimuth_deg"]),
                tilt_deg=float(params_data["tilt_deg"]),
                climate_zone=params_data.get("climate_zone", "central_europe"),
            )
        elif series_type == SeriesType.BESS:
            return BESSParameters(
                capacity_kwh=float(params_data["capacity_kwh"]),
                max_charge_power_kw=float(params_data["max_charge_power_kw"]),
                max_discharge_power_kw=float(params_data["max_discharge_power_kw"]),
                efficiency_pct=float(params_data["efficiency_pct"]),
                strategy=BESSStrategy(params_data["strategy"]),
                peak_shaving_threshold_kw=params_data.get("peak_shaving_threshold_kw"),
            )
        raise ValueError(f"Unbekannter series_type: {series_type}")

    @staticmethod
    def _load_ps_node(node_data: dict) -> PSNode:
        """Deserialize a PSNode tree from a dict."""
        children = [
            ProjectService._load_ps_node(c) for c in node_data.get("children", [])
        ]
        return PSNode(
            node_id=node_data["node_id"],
            node_type=PSNodeType(node_data["node_type"]),
            name=node_data.get("name", ""),
            simultaneity_factor=float(node_data.get("simultaneity_factor", 1.0)),
            children=children,
            profile_type=node_data.get("profile_type"),
            annual_energy_kwh=node_data.get("annual_energy_kwh"),
        )
