# Contract: ProjectService

**Module**: `src/services/project_service.py`  
**Date**: 2026-03-21

---

## Responsibilities

- Create new projects with UUID and seed
- Validate mandatory metadata before export
- Serialise / deserialise projects to/from JSON
- Switch the active project in session state

---

## Interface

### `ProjectService.create(kunde, ersteller, adresse, seed=None) -> Project`

Creates a new `Project` with a generated UUID4 and assigns `target_year = current_year - 2`.

**Preconditions**: none (fields may be empty at creation; validation is deferred to export)  
**Postconditions**: returned `Project` has a unique `uuid`, `created_at` set to current UTC, `load_series = []`, `static_limits` with all fields `None`  
**Raises**: nothing  
**Seed**: if `seed` is `None`, a random integer is generated via `secrets.randbelow(2**31)`

---

### `ProjectService.validate_for_export(project: Project) -> list[str]`

Returns a list of German validation error strings. Empty list = valid.

**Rules**:
- `project.kunde` MUST be non-empty string (strip whitespace)
- `project.ersteller` MUST be non-empty string
- `project.adresse` MUST be non-empty string

**Returns**: e.g. `["Pflichtfeld 'Kunde' ist leer.", "Pflichtfeld 'Adresse' ist leer."]`  
**Raises**: nothing

---

### `ProjectService.to_json(project: Project) -> str`

Serialises a `Project` to a JSON string (schema v1.0).

**Preconditions**: `validate_for_export(project)` returns `[]`  
**Postconditions**: returned string is valid JSON; round-trip via `from_json` reproduces identical `Project`  
**Raises**: `ValueError` if validation fails (caller must validate first)

---

### `ProjectService.from_json(raw_json: str) -> Project`

Deserialises a JSON string to a `Project`.

**Preconditions**: `raw_json` is a valid UTF-8 JSON string  
**Postconditions**: returned `Project` has all fields populated; unknown `series_type` entries in `load_series` are skipped (a list of skipped names is attached as `project._skipped_series: list[str]` for UI display)  
**Raises**: `ValueError` with German message if JSON is malformed or `schema_version` is unknown

---

### `ProjectService.switch_active(session_state, uuid: str) -> None`

Sets `session_state["active_project_uuid"] = uuid`.

**Preconditions**: `uuid` exists in `session_state["projects"]`  
**Raises**: `KeyError` if UUID not found

---

## Error Messages (German)

All errors returned or raised by this service MUST be in German and free of stack traces.

| Condition | Message |
|---|---|
| Kunde empty | `"Pflichtfeld 'Kunde' ist leer."` |
| Ersteller empty | `"Pflichtfeld 'Ersteller' ist leer."` |
| Adresse empty | `"Pflichtfeld 'Adresse' ist leer."` |
| JSON malformed | `"Die Projektdatei konnte nicht gelesen werden. Bitte prüfen Sie das Dateiformat."` |
| Unknown schema version | `"Unbekannte Schema-Version '{version}'. Bitte verwenden Sie eine kompatible Programmversion."` |
| UUID not found | `"Projekt mit ID '{uuid}' nicht gefunden."` |
