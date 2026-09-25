# Bellabeat Fitness Data Analytics — Streamlit Dashboard

A full case-study deliverable for the Bellabeat marketing-analytics brief: clean the Fitbit
tracker data into a queryable SQLite database, then explore it through an interactive
Streamlit dashboard with a built-in SQL analysis workbench.

## What's inside

```
bellabeat_dashboard/
├── build_database.py   # Reads the raw CSVs and builds data/bellabeat.db (run once)
├── app.py               # The Streamlit dashboard (8 pages, incl. SQL workbench)
├── requirements.txt
├── data/
│   └── bellabeat.db     # Pre-built SQLite database (already generated for you)
└── README.md
```

## Run it locally

1. Unzip/copy this folder to your machine.
2. Create a virtual environment (recommended) and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. `data/bellabeat.db` is already built and included. If you ever want to rebuild it from the
   raw CSVs (e.g. after editing `build_database.py`), point `RAW` in that file at your CSV
   folder and run:
   ```bash
   python build_database.py
   ```
4. Launch the app:
   ```bash
   streamlit run app.py
   ```
   It will open at `http://localhost:8501`.

## Dashboard pages

- **Overview** — KPIs and weekday activity/sedentary patterns.
- **Activity** — steps/calories by weekday, per-user heat-mapped weekday table, hourly patterns.
- **Sleep** — sleep duration, sleep efficiency, and a steps-vs-sleep correlation scatter plot.
- **Heart Rate** — hourly heart-rate patterns and a per-user summary (aggregated from 2.4M
  second-level readings for performance).
- **Weight** — weight/BMI trends for the small subset of users who logged weight.
- **SQL Analysis** — a live SQL workbench: browse the schema, pick an example query or write
  your own `SELECT`, run it against `bellabeat.db`, view/download results, and auto-chart them.
- **Insights & Recommendations** — the write-up: key findings and marketing recommendations.
- **About the Data** — data source, licensing, known limitations, and full documentation of
  every cleaning/aggregation decision made in `build_database.py`.

## Data source & cleaning notes

See the **About the Data** page inside the app (or the docstring at the top of
`build_database.py`) for the full write-up of data provenance, limitations, and every cleaning
step applied — this doubles as the "description of data sources" and "documentation of
cleaning" deliverables required by the case study brief.
