# SIH 26103 — Infrastructure Project Monitoring

Initial application scaffold and SQLite persistence layer for the monitoring MVP.

## Setup

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn backend.app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; health is at `/api/health`.
The relative SQLite URL is always resolved from this repository root, regardless of the current working directory.

Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env` before using administrative endpoints. Obtain a short-lived bearer token with `POST /api/auth/login` and send it as `Authorization: Bearer <token>` when uploading CSV files. Tokens are held in process memory for the single-instance MVP. Set `ALLOWED_ORIGINS` to a comma-separated list of trusted frontend origins; the default allows the Vite development URLs.

`POST /api/projects/upload` validates and atomically imports a project CSV for authenticated administrators. Send the optional `source_as_of_date` as a `YYYY-MM-DD` multipart form field; omit it when the report date is unknown. Re-uploading identical bytes returns the existing dataset instead of duplicating records.

`GET /api/datasets/{dataset_id}/quality?offset=0&limit=100` returns grouped quality counts and paginated record-level issues. Only completed datasets are exposed. Accepted rows may contain warnings or informational flags; rejected rows contain validation errors and are not written as project snapshots.

Start the frontend in another terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

The default `GROQ_MODEL` is `openai/gpt-oss-20b`, a Groq production model with tool use and strict structured-output support at the time of implementation. Health reports the assistant as disabled until `GROQ_API_KEY` is set. Keep the key only in `.env`; never commit it. Model availability can change, so override `GROQ_MODEL` when Groq retires or replaces it.

The grounded assistant is available at `POST /api/assistant/query` with JSON such as `{"question":"Which projects have the highest stored risk?"}`. It supports ranking, project explanations, group summaries, and peer comparisons. Retrieval is limited to allowlisted SQLAlchemy queries over completed datasets and stored model results. When Groq is unavailable, the response reports `provider_status: "fallback"` or `"disabled"` and returns only the deterministic retrieved summary with caveats.

## SQLite operation

The database uses foreign-key enforcement, a five-second busy timeout, and WAL mode. SQLite supports concurrent readers but serializes writes, so the MVP should run as one application instance and keep transactions short. Monetary values use `NUMERIC(18, 2)` in crore and are rounded to two decimal places when written.

Use the SQLite-aware helpers in `backend.app.services.database_backup` for consistent backup and restore operations. Keep the database and its WAL/SHM files on a persistent local volume when containerizing.
Close and dispose application database connections before restoring over an existing database file.

Run verification with:

```powershell
python -m pytest
```

## Reproduce the demo

Start the backend and frontend as described above, set `ADMIN_PASSWORD` in the current environment, and run the complete flow from the repository root:

```powershell
$env:ADMIN_PASSWORD = "your-local-admin-password"
python scripts/demo.py
```

The script uploads `DATA/Projects_Report.csv`, prints the quality report, trains both target models with seed `42`, persists risk scores, loads the dashboard and project explanation, requests a benchmark, and asks the grounded assistant for the highest-risk projects. It records stage timings and the Python/platform/CPU conditions in its JSON output. Use `--skip-training` when model artifacts and scores already exist, or pass `--report` and `--source-as-of-date` for another snapshot.

Latest local demonstration evidence: Windows 11, Python 3.12.4, 8 CPUs; 1,775 records imported in `0.098s`, dashboard summary loaded in `1.367s`, and the configured Groq assistant returned in `3.369s`. Training took `8.559s` and persisted scoring took `56.278s`. These are machine- and provider-dependent measurements, not service-level guarantees. The run produced 662 high-risk and 167 critical projects from the snapshot.

The supplied snapshot is an analytical classification prototype. It does not establish future forecasting validity, and missing revised costs, dates, model outputs, or sparse peer cohorts remain explicitly unavailable. The assistant cannot create or change predictions.

## Docker

Copy `.env.example` to `.env`, replace the local admin password, and inject `GROQ_API_KEY` only through that backend environment file. Then run:

```powershell
docker compose up --build
```

The frontend is available at `http://localhost:5173` and the API at `http://localhost:8000`. SQLite data is persisted in the `project-data` volume and model artifacts in `model-artifacts`; the frontend image receives only the public API URL and never receives the Groq secret. Stop the stack with `docker compose down`; do not add `--volumes` when you need to preserve demo data.

Train the T05 snapshot classifiers after importing a completed dataset:

```powershell
python -m ml.training.train --dataset-id 1 --analysis-date 2026-09-13 --seed 42
```

Use the actual analytical date intended for the report. The command trains and calibrates logistic regression and XGBoost for both targets, registers reproducible model metadata in SQLite, and writes ignored runtime artifacts under `artifacts/models/`. See `DOC/ModelEvaluation.md` for the current held-out results and limitations.

Persist scores after training with:

```powershell
python -m ml.training.score --dataset-id 1 --analysis-date 2026-09-13
```

The score command is idempotent for a dataset, stores selected model references and the versioned `risk-rules-v1` result, and keeps all application persistence in SQLite. SQLite backup and restore remain available through `backend.app.services.database_backup`.
