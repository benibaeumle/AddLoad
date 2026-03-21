# Quickstart: SLP Clickdummy

**Branch**: `001-slp-clickdummy` | **Date**: 2026-03-21

---

## Prerequisites

- Python 3.11 or 3.12 installed (`python --version`)
- `pip` available
- A modern browser (Chrome, Firefox, Edge)

---

## 1. Clone / Enter the Repository

```bash
cd /path/to/AddLoad
```

---

## 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows PowerShell
```

---

## 3. Install Runtime Dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` contains:

```
streamlit>=1.32
pandas>=2.1
numpy>=1.26
plotly>=5.19
openpyxl>=3.1
```

---

## 4. Install Development Dependencies (optional, for tests)

```bash
pip install -r requirements-dev.txt
```

`requirements-dev.txt` contains:

```
pytest>=8.0
pytest-cov>=4.1
pytest-benchmark>=4.0
hypothesis>=6.98
ruff>=0.3
black>=24.0
pre-commit>=3.6
```

Set up pre-commit hooks:

```bash
pre-commit install
```

---

## 5. Run the Application

```bash
streamlit run app.py
```

Streamlit will print a local URL (default: `http://localhost:8501`). Open it in
your browser. No internet connection is required after the first run.

---

## 6. Basic Usage

1. **Neues Projekt**: Click "Neues Projekt erstellen" in the sidebar. Fill in Kunde,
   Ersteller, Adresse.
2. **Lastgang hinzufügen**: Navigate to "Lastgänge" → choose a type (SLP, CSV, PS,
   PVA, BESS) → fill in the form → click "Hinzufügen".
3. **Chart ansehen**: Navigate to "Chart". Use scroll/drag to zoom and pan.
4. **Exportieren**: Navigate to "Export" → download CSV or JSON.
5. **Projekt laden**: In the sidebar, use "Projekt laden" to upload a previously
   saved project JSON file.

---

## 7. Run Tests

```bash
# All tests with coverage report
pytest --cov=src --cov-report=term-missing

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Performance benchmarks (outputs benchmark results)
pytest tests/benchmarks/ --benchmark-only
```

Coverage threshold is enforced at 80%. A failing coverage gate blocks CI.

---

## 8. Lint and Format

```bash
# Check linting
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Format code
black src/ tests/
```

---

## 9. Reproducibility

Each project stores a `seed` integer. The seed controls all stochastic components
(PV cloud-cover variation, BESS Arbitrage price curve). To reproduce results exactly,
ensure you load the same project JSON file — the seed is preserved in the file.

To set a specific seed when creating a project programmatically:

```python
from src.services.project_service import ProjectService
project = ProjectService.create(kunde="Test", ersteller="Dev", adresse="Teststr. 1", seed=42)
```

---

## 10. Target Year

The application automatically sets `target_year = current_year - 2` when a new
project is created. This can be inspected in the project JSON under `"target_year"`.
All time series in the project are anchored to this year. Changing the target year
requires creating a new project.

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: streamlit` | Virtual env not activated or deps not installed | Activate venv and re-run `pip install -r requirements.txt` |
| Chart not updating after series change | Streamlit rerun not triggered | Click anywhere on the page or use the "Aktualisieren" button |
| CSV upload rejected (resolution mismatch) | File has wrong number of rows | Ensure file has exactly 35040 rows (or 35136 for leap years) |
| BESS profile is all zeros | No other load series in project | Add at least one SLP, CSV, or PS series before adding BESS |
| `ValueError: Unbekannte Schema-Version` | Project JSON from a future version | Use the version of the app that created the file |
