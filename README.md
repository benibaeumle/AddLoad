# SLP Lastgang-Verwaltung

A Streamlit app for managing, aggregating, and exporting electricity load profiles based on BDEW standard load profiles (SLP). Supports BESS (battery energy storage) simulation and peak-shaving analysis.

## Features

- **Load series management** — create and manage named load series per project
- **BDEW profiles** — built-in normalised profiles (H0, G0–G6, L0–L2)
- **BESS simulation** — peak shaving, self-consumption (*Eigenverbrauch*), and arbitrage strategies
- **Limits & thresholds** — define power limits and visualise breaches
- **Chart view** — interactive Plotly charts
- **Export** — download aggregated load data as Excel (`.xlsx`) or CSV

## Quickstart

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Project structure

```
app.py                  # Streamlit entry point
src/
  generators/           # BESS simulator, CSV parser, SLP generator
  models/               # Domain models (LoadSeries, Project, …)
  services/             # Project persistence and load registry
  ui/pages/             # One module per app page
data/bdew/              # Normalised BDEW profile CSVs
```

## Development

```bash
pip install -r requirements-dev.txt
pre-commit install

pytest                  # run unit + integration tests
pytest --benchmark-only # run benchmarks
```
