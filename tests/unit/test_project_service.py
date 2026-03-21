"""Unit tests for ProjectService."""

from __future__ import annotations

import json

import pytest

from src.services.project_service import ProjectService


def test_create_returns_project():
    p = ProjectService.create(kunde="K", ersteller="E", adresse="A")
    assert p.kunde == "K"
    assert p.ersteller == "E"
    assert p.adresse == "A"
    assert p.schema_version == "1.0"
    assert len(p.load_series) == 0


def test_create_target_year():
    from datetime import datetime, timezone
    p = ProjectService.create(kunde="K", ersteller="E", adresse="A")
    expected = datetime.now(timezone.utc).year - 2
    assert p.target_year == expected


def test_create_with_seed():
    p = ProjectService.create(kunde="K", ersteller="E", adresse="A", seed=42)
    assert p.seed == 42


def test_validate_for_export_empty_fields():
    p = ProjectService.create(kunde="", ersteller="", adresse="")
    errors = ProjectService.validate_for_export(p)
    assert len(errors) == 3


def test_validate_for_export_valid():
    p = ProjectService.create(kunde="K", ersteller="E", adresse="A")
    errors = ProjectService.validate_for_export(p)
    assert errors == []


def test_to_json_raises_on_empty_fields():
    p = ProjectService.create(kunde="", ersteller="", adresse="")
    with pytest.raises(ValueError):
        ProjectService.to_json(p)


def test_to_json_valid_project():
    p = ProjectService.create(kunde="K", ersteller="E", adresse="A", seed=0)
    json_str = ProjectService.to_json(p)
    data = json.loads(json_str)
    assert data["schema_version"] == "1.0"
    assert data["kunde"] == "K"


def test_from_json_roundtrip():
    p = ProjectService.create(kunde="K", ersteller="E", adresse="A", seed=7)
    json_str = ProjectService.to_json(p)
    loaded, skipped = ProjectService.from_json(json_str)
    assert skipped == []
    assert loaded.uuid == p.uuid
    assert loaded.seed == 7


def test_from_json_unknown_version_raises():
    data = {"schema_version": "99.0", "uuid": "x", "load_series": []}
    with pytest.raises(ValueError, match="Unbekannte Schema-Version"):
        ProjectService.from_json(json.dumps(data))


def test_from_json_invalid_json_raises():
    with pytest.raises(ValueError, match="Ungültiges JSON"):
        ProjectService.from_json("not json {{{")


def test_switch_active():
    state = {"projects": {}, "active_project_uuid": None}
    ProjectService.switch_active(state, "abc")
    assert state["active_project_uuid"] == "abc"


def test_save_and_load_all_from_disk(tmp_path):
    p = ProjectService.create(kunde="K", ersteller="E", adresse="A", seed=1)
    projects = {p.uuid: p}
    path = str(tmp_path / "projects.json")

    ProjectService.save_all_to_disk(projects, p.uuid, path)
    loaded_projects, active_uuid, skipped = ProjectService.load_all_from_disk(path)

    assert active_uuid == p.uuid
    assert skipped == []
    assert p.uuid in loaded_projects
    loaded = loaded_projects[p.uuid]
    assert loaded.kunde == "K"
    assert loaded.seed == 1


def test_load_all_from_disk_missing_file(tmp_path):
    path = str(tmp_path / "nonexistent.json")
    projects, active_uuid, skipped = ProjectService.load_all_from_disk(path)
    assert projects == {}
    assert active_uuid is None
    assert skipped == []


def test_load_all_from_disk_corrupt_file(tmp_path):
    path = str(tmp_path / "corrupt.json")
    with open(path, "w") as fh:
        fh.write("not valid json {{{")
    projects, active_uuid, skipped = ProjectService.load_all_from_disk(path)
    assert projects == {}
    assert active_uuid is None


def test_save_all_to_disk_atomic_write(tmp_path):
    p = ProjectService.create(kunde="K", ersteller="E", adresse="A", seed=2)
    projects = {p.uuid: p}
    path = str(tmp_path / "projects.json")
    ProjectService.save_all_to_disk(projects, p.uuid, path)
    import os
    assert os.path.exists(path)
    assert not os.path.exists(path + ".tmp")
