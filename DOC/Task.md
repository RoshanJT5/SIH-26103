# Implementation Tasks — SIH 26103

Prepared: 2026-09-13

## 1. Scope and architecture decisions

Build the infrastructure project monitoring MVP described in the existing documents, using **SQLite for the database** and **LangChain-Groq (`langchain-groq`, `ChatGroq`) for the LLM integration**. These choices supersede the PostgreSQL and unspecified/self-hosted LLM recommendations in `DOC/Techstack.MD` for this implementation. The assistant is included in this delivery plan even though earlier documents describe it as optional.

This file is the implementation backlog. Tasks T01 and T02 now provide the initial application scaffold, dependency manifests, database, migration, and persistence tests. Existing source documents and this task file are under `DOC/`.

| Layer | Selected technology and responsibility |
|---|---|
| Frontend | React, TypeScript, Tailwind CSS, Recharts; dashboard and assistant |
| Backend | Python, FastAPI, Pydantic, Uvicorn; validation and application services |
| Database | SQLite with SQLAlchemy and Alembic; persistent project and model records |
| Data | Pandas and NumPy; ingestion, validation, analytical features |
| ML | Scikit-learn logistic regression baseline and XGBoost candidate |
| Explainability | SHAP for individual trained models; explicit rules for implementation indicators |
| LLM | LangChain-Groq calling a configurable Groq-hosted model |
| Retrieval | Validated application queries over SQLite and stored model results |
| Testing | Pytest for backend/ML; frontend integration and end-to-end checks |
| Deployment | Local development first; Docker with a persistent SQLite volume |

Flow: CSV → validation → SQLite → analytics/ML → stored risk and SHAP results → FastAPI → dashboard. Assistant flow: question → validated intent → bounded SQLite retrieval → grounded context → ChatGroq → answer with source references.

Groq is a hosted service requiring credentials and network access. Keep the key on the backend. A vector database and document embeddings are unnecessary for the structured-data MVP.

## 2. File-by-file analysis

| Existing file | Role and implementation implications |
|---|---|
| `DOC/PRD.md` | Defines users, ingestion, portfolio filters, cost/time risk, ranking, explanations, alerts, benchmarking, assistant, APIs, and acceptance criteria. Use as the functional requirements baseline. |
| `DOC/MVP.md` | Defines the demonstration scope and sample scoring. Retain its snapshot-data limitation. Its example table labels score 31 as Low despite the specified Medium band; implement one shared band function rather than copying examples. |
| `DOC/Approach.MD` | Defines data → baseline → ML → SHAP → product → assistant delivery order. Preserve leakage controls and distinguish observed indicators from model explanations. Historical forecasting remains future work. |
| `DOC/Techstack.MD` | Supplies the proposed layers, repository structure, security, and performance targets. Replace PostgreSQL and a dedicated local LLM service in the implementation plan with SQLite and ChatGroq. |
| `DATA/Projects_Report.csv` | Actual input data: quoted CSV with a report-title row, a blank row, and multiline column headers. Requires CSV-aware parsing and explicit header normalization. |

### Dataset findings

The complete CSV was parsed for record counts, uniqueness, missing fields, numeric validity, and date validity.

| Check | Observed result |
|---|---:|
| Project records / columns | 1,775 / 13 |
| Unique project codes | 1,775; no duplicate codes |
| Sectors / ministries / implementing agencies | 22 / 17 / 186 |
| Blank revised commissioning dates | 348 |
| Blank sanction dates | 12 |
| Blank values in other columns | 0 |
| Zero revised costs | 833 |
| Zero expenditure values | 135 |
| Zero physical-progress values | 92 |
| Nonpositive original costs | 0 |
| Unparseable numeric values / negative numeric values | 0 / 0 |
| Physical progress outside 0–100 | 0 |
| Invalid nonblank dates under `dd/MM/yyyy` | 0 |

Costs and expenditure are in crore; progress is a percentage. The file contains no explicit snapshot/report date or historical monthly sequence. These checks do not establish the business meaning of zero revised costs or validate real-world accuracy.

Critical data policy: preserve original values. Until the source convention is established, treat zero revised cost as unavailable for escalation labels and revised-budget ratios, not as an actual zero budget or proof of no overrun. Missing revised dates likewise produce unknown schedule labels, not automatic negative labels. Record exclusion counts and assess resulting selection bias before training.

## 3. Ordered task backlog

All unchecked items below are pending implementation. Complete each acceptance gate before dependent tasks.

### T01 — Scaffold and configuration (P0)

- [x] Create `backend/app/{api,schemas,models,services}`, `frontend/src`, `ml/{features,training,evaluation}`, `database/migrations`, and `tests`.
- [x] Add compatible, pinned dependencies and reproducible installation commands. Include `langchain-groq`, `langchain-core`, SQLAlchemy, Alembic, FastAPI, Pandas, scikit-learn, XGBoost, and SHAP.
- [x] Add `.env.example` with `DATABASE_URL=sqlite:///./database/project_monitoring.db`, `GROQ_API_KEY=`, and `GROQ_MODEL=`. Resolve the database path against a documented application root.
- [x] Select a currently available Groq model supporting the required structured output/tool behavior; validate configuration rather than assuming a permanent model identifier.
- [x] Ignore real `.env` files, SQLite runtime files including WAL/SHM companions, generated models, and caches. Preserve the supplied CSV.
- [x] Add a health endpoint and startup instructions. Missing Groq credentials must disable assistant generation cleanly without blocking analytics.

Acceptance: a clean install starts the backend and frontend; configuration contains no committed credentials.

### T02 — SQLite schema and persistence (P0; depends on T01)

- [x] Create versioned migrations for the following tables.

| Table | Required data and constraints |
|---|---|
| `datasets` | ID, source name, checksum, import timestamp, nullable source as-of date, status, accepted/rejected counts; checksum supports idempotency |
| `projects` | ID and unique text project code |
| `project_snapshots` | Project/dataset foreign keys; project name, sector, ministry, agency, costs, expenditure, progress, dates, raw values and quality flags; unique `(project_id, dataset_id)` |
| `ingestion_issues` | Dataset, source record number, field, raw value, issue code, severity |
| `model_versions` | Target definition, feature schema, artifact reference/checksum, training dataset, split seed, metrics, calibration metadata |
| `risk_predictions` | Snapshot/model references, cost/time probabilities, rule version, implementation score, overall score, band, timestamp, availability status |
| `risk_explanations` | Prediction and component-model references, feature/value, SHAP contribution, baseline and output scale |
| `alerts` | Snapshot/prediction, rule version, severity, message, status and timestamp; deduplication key |
| `audit_events` | Operation, timestamp, dataset/model references and outcome; no credentials |

- [x] Use explicit column types, nullability, uniqueness, and range checks. Store dates as ISO dates and UTC event timestamps. Document monetary precision and rounding.
- [x] Enable foreign-key enforcement on each connection, configure a bounded busy timeout, and initialize WAL mode. Use short transactions and request-scoped sessions; do not hold write transactions during ML or Groq calls.
- [x] Index dataset/project joins and common sector, ministry, agency, and risk filters.
- [x] Commit imports atomically; expose only completed datasets. Keep repeated uploads idempotent and later datasets distinct.
- [x] Support backup/restore through a SQLite-aware backup operation and persistent local storage. Account for SQLite's single concurrent writer; use one application instance for the initial demo.

Acceptance: migrations create a fresh database; restart preserves records; duplicate imports, rollback, foreign keys, and backup restoration are verified.

### T03 — Ingestion and quality report (P0; depends on T02)

- [x] Implement `POST /api/projects/upload` with file-size limits and content/schema validation.
- [x] Recognize the title/preamble and quoted multiline header; normalize whitespace before applying a fixed column mapping.
- [x] Map the 13 fields to `source_row_number`, `sector`, `ministry`, `implementing_agency`, `project_code`, `project_name`, `original_cost_cr`, `revised_cost_cr`, `expenditure_cr`, `physical_progress_pct`, `original_commissioning_date`, `revised_commissioning_date`, and `sanction_date`.
- [x] Parse dates day-first with the explicit source format. Preserve project codes as text and missing values as null.
- [x] Flag malformed records, invalid ranges, conflicting duplicate codes, inconsistent date ordering, zero revised costs, and expenditure above reported budgets for review; do not silently correct plausible anomalies.
- [x] Expose quality counts and record-level reasons through a dataset-quality endpoint. Distinguish rejected records from accepted records with unavailable fields.
- [x] Accept a nullable source as-of date as metadata. Never silently substitute import time for the actual reporting date.

Acceptance: the supplied file yields 1,775 distinct project records and reproduces the quality counts above. Tests include malformed CSV, embedded newlines, missing headers, duplicate codes, and repeat uploads.

### T04 — Analytics and leakage-safe features (P0; depends on T03)

- [x] Calculate observed cost increase, cost escalation percentage, schedule revision days, and expenditure ratios only with valid inputs; undefined values remain null.
- [x] Calculate project age against an explicit analysis date, clearly marked if the source as-of date is unavailable.
- [x] Maintain separate analytical and model feature schemas. Cost-model inputs must exclude revised cost and all its derivatives, including revised-cost expenditure ratios. Time-model inputs must exclude revised commissioning date and derived delay indicators.
- [x] Audit remaining features for post-outcome information. Exclude project codes/names as predictors and fit encoding/imputation only on training data.
- [x] Define and version labels using valid revised cost versus original cost and valid revised versus original commissioning dates. Missing evidence means unknown; never impute targets.

Acceptance: denominator/missing-data tests pass, label eligibility counts are reported, and prohibited features cannot enter training.

### T05 — Baseline, ML evaluation, and SHAP (P0; depends on T04)

- [x] Train separate logistic regression and XGBoost candidates for cost and time labels using reproducible splits and identical eligible evaluation records per target.
- [x] Check class balance and sample sufficiency before splitting; report an unavailable model if evaluation is not supportable.
- [x] Keep held-out test data untouched during preprocessing, tuning, threshold selection, and calibration. Prevent project overlap if future imports introduce multiple snapshots.
- [x] Report precision, recall, F1, ROC-AUC, PR-AUC, confusion matrices, and calibration. Explain undefined metrics and compare candidates honestly; do not assume XGBoost wins.
- [x] Save fitted preprocessing, model artifacts, feature order, target definitions, metrics, and dataset/model versions.
- [x] Generate local/global SHAP explanations for the corresponding component model. Persist baseline and output scale; do not present raw log-odds contributions as percentage points or as explanations of the blended overall score.
- [x] Label results as snapshot risk-classification estimates. Excluding direct leakage alone does not establish future predictive validity.

Acceptance: training and inference are reproducible; held-out results and model-derived explanations are available; no unsupported accuracy or forecasting claims appear.

### T06 — Risk, alerts, and benchmarks (P0; depends on T05)

- [x] Define a transparent, versioned 0–100 implementation-risk rule using supported indicators. Document thresholds and missing-input behavior; do not invent expected progress.
- [x] Convert component probabilities to 0–100 before applying `0.40 * cost + 0.40 * time + 0.20 * implementation`.
- [x] Use continuous bands: Low `[0,30]`, Medium `(30,60]`, High `(60,80]`, Critical `(80,100]`. Missing components produce unavailable overall risk unless an explicitly documented alternative is implemented.
- [x] Generate deduplicated in-app alerts and rule-based suggested monitoring focus. Initial snapshot alerts indicate current status; threshold crossings require comparable successive observations.
- [x] Compare projects within documented sector/ministry/cost cohorts, excluding the subject from peers. Show cohort size and suppress percentiles below a configurable minimum (initially 10 peers).

Acceptance: boundary values, null scores, alert deduplication, and sparse cohorts behave consistently across API and UI.

### T07 — Application APIs (P0; depends on T03–T06)

- [x] Implement project list/detail, dashboard summary, sector/ministry analytics, benchmarks, risk list/detail/explanation, and alert endpoints from the PRD.
- [x] Apply shared dataset, sector, ministry, agency, risk, cost, and progress filters to both lists and aggregates.
- [x] Add pagination, bounded limits, deterministic sorting, parameterized database access, consistent errors, and dataset/model freshness metadata.
- [x] Restrict upload/rescoring/admin operations and implement the documented login flow; configure allowed frontend origins.

Acceptance: API integration tests verify filter/aggregate agreement, pagination, unknown IDs, access restrictions, and missing predictions.

### T08 — Dashboard and investigation views (P0; depends on T07)

- [x] Build portfolio cards, sortable risk ranking, sector/ministry charts, cost-versus-time risk scatter, and shared filters.
- [x] Build project detail with raw facts, observed deviations, component probabilities, SHAP drivers, peer comparisons, and monitoring suggestions.
- [x] Show quality warnings, eligible-record denominators, dataset freshness, model versions, loading/error/empty states, and unknown risk values.
- [x] Provide visible snapshot-data limitations and distinguish facts, estimates, and suggestions.

Acceptance: users can upload, filter, rank, open a project, inspect explanations, and compare peers; displayed totals match API results.

### T09 — LangChain-Groq assistant (P0 for requested scope; depends on T07)

- [x] Implement a backend client using `from langchain_groq import ChatGroq`, reading `GROQ_API_KEY` and `GROQ_MODEL` from configuration with bounded timeout/retries.
- [x] Implement `POST /api/assistant/query` and a frontend chat panel.
- [x] Parse questions into validated intents: list/rank projects, explain project risk, summarize a sector/ministry, and compare peers. Validate structured outputs before retrieval.
- [x] Implement allowlisted retrieval functions backed by parameterized SQLAlchemy queries, with bounded result sizes. Do not execute unrestricted LLM-generated SQL or expose writes to the assistant.
- [x] Resolve ambiguous project names before making project-specific claims. Return explicit no-data responses when records or predictions are unavailable.
- [x] Supply only relevant project facts, stored probabilities, SHAP output, benchmark summaries, and source IDs to ChatGroq. Treat imported text as data rather than instructions.
- [x] Return answer text plus project IDs, dataset/model references, and applicable caveats. Compute numeric aggregates in backend queries rather than asking the model to calculate them.
- [x] Handle invalid credentials, rate limits, timeouts, invalid structured responses, and provider outages with clear errors or deterministic retrieved summaries. Never fabricate replacement answers.
- [x] Log latency, selected model and request outcome without secrets or unnecessary full prompts.

Acceptance: test highest-risk projects, sector filters, explanations, comparison, ambiguous names, unknown projects, injection attempts, and Groq failures. Unit tests use a mocked provider; a configured live smoke test verifies actual integration. LLM output never creates or changes risk scores.

### T10 — Integration, documentation, and demo (P0; depends on T08–T09)

- [x] Run an end-to-end flow: CSV import → quality report → train/evaluate → score → dashboard → project explanation → benchmark → grounded assistant answer.
- [x] Measure import time (target under 10 seconds for this dataset), dashboard load (under 3 seconds), and assistant latency (target under 10 seconds, provider-dependent), recording hardware and conditions.
- [x] Document setup, environment variables, migrations, ingestion, training, tests, SQLite backup/restore, model refresh, and known limitations in a README.
- [x] Supply Docker configuration with a persistent database volume and backend-only Groq secret injection.
- [x] Add a demo script using real project codes and measured model results. Reconcile legacy stack recommendations with this task plan during implementation.

Acceptance: a new developer can reproduce the demo from documented steps; data survives restart; the assistant uses ChatGroq and all application persistence uses SQLite.

## 4. Deferred work

Historical monthly imports, temporal validation, progress trajectories, validated future warning forecasts, document RAG, PAIMANA API integration, external notifications, and what-if interventions are future milestones. No autonomous agency contact or policy decisions belong in the MVP.

## 5. Technical references

- [LangChain ChatGroq integration](https://docs.langchain.com/oss/python/integrations/chat/groq) — integration package and credential setup.
- [ChatGroq API reference](https://reference.langchain.com/python/langchain-groq/chat_models/ChatGroq) — client configuration and supported methods.
- [SQLite PRAGMA reference](https://www.sqlite.org/pragma.html) — connection settings and busy timeout.
- [SQLite foreign-key support](https://www.sqlite.org/foreignkeys.html) — per-connection enforcement.
- [SQLite write-ahead logging](https://www.sqlite.org/wal.html) — WAL operation and concurrency constraints.
