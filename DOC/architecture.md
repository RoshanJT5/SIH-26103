# Architecture — SIH 26103 (16-feature)

## Stack
FastAPI (Python 3.12) + Pydantic + SQLAlchemy + Alembic + SQLite (WAL, FK, 5s timeout) + scikit-learn/XGBoost + SHAP + LangChain-Groq. Frontend React 19 + Vite + React Router + Recharts + Tailwind. Single SQLite writer, short transactions, request-scoped sessions.

## Data & ML
CSV → ingestion (preamble/header, 13 cols, SHAP) → datasets/projects/snapshots/ingestion_issues → analytical features (`features.py`, never invent progress) → leakage-safe schemas (cost blocks revised_cost, time blocks revised_date) → train (`ml/training`, group-safe splits, LR+XGB, calibration) → model_versions → score → risk_predictions/risk_explanations/alerts. Project matched by stable `project_id` across snapshots.

## Risk & Services
- `risk.py` `risk-rules-v1`: implementation score 0-100, blended `0.40*cost+0.40*time+0.20*impl`, bands low/medium/high/critical
- `trends.py` `risk-trends-v1`: thresholds improving ≤-5, stable -5..5, watch 5..10, deteriorating 10..20, rapid >20
- `intervention.py` `intervention-v1`: 0.35 overall +0.15 deterioration +0.15 cost +0.15 time +0.10 exposure +0.10 deviation, drivers
- `early_warning.py` `early-warning-v1`: deterministic signals risk_escalation/progress_deviation/cost_escalation/schedule_slippage/rapid_deterioration/expenditure_deviation, dedup key, populates on read/scoring
- `confidence.py`: data_quality from ingestion issues + missing fields, high/medium/low tiers
- `trajectory.py`: expected = age/planned*100, deviation
- `forecast.py`: observed + dashed linear-trend `horizon=3`, limitations disclosed
- `simulation.py`: heuristic read-only variant, never persists
- `recommendations.py`: 1-5 rules from schedule/cost/deviation/band
- `reporting.py`: 7-section brief (summary, facts, deviations, drivers, benchmark, recommendations, limitations)
- `analytics_extra.py`: cost drivers (avg SHAP), ministry health, geography (ministry proxy, illustrative), timeline, model registry/performance

## API Layer (`backend/app/api`)
monitoring.py (helpers _latest_prediction), trends.py, interventions.py, early_warnings.py (admin auth), project_extensions.py (confidence/trajectory/forecast/simulation/recommendations/report), analytics_extra.py (cost-drivers, ministry health, geography, timeline, ml models), updates.py (platform updates). All with Pydantic schemas, OpenAPI docs, paginated, filtered, unavailable states.

## Assistant
8 intents (rank, explain, summarize, compare, find_deteriorating_projects, list_early_warnings, show_priority, show_cost_drivers). Retrieval via parameterized SQLAlchemy only; Groq when key present else fallback deterministic summary with caveats and sources.

## Frontend
GovLayout with dropdown nav (Monitoring: Overview/Changes/Early Warnings/Intervention/Risk Trends; Analytics: 7 items), Login/Sign Up on right (44px, secondary/primary), single-line nowrap typography, mobile grouped nav. Routes: Home, Dashboard, Monitoring, Projects, Analytics, Simulation, Documents, Updates (/updates + /updates/:id with category/search filters, timeline, featured card, 4 states), Help, plus Login/Signup. Home preview shows 3 latest live updates with View All → /updates. 10-block DashboardPage, 13-section ProjectDetailPage, Recharts (title/units/text alternative + reduced-motion), 3-4 meaningful images, api.tsx pattern, loading/error/empty/unavailable, accessibility.

## Persistence
Alembic 0001 + 0002 early_warnings + 0003 platform_updates (category/title/summary/content/status/related_dataset_id/published_at/updated_at/created_at/meta; 5 seeded updates). Backup/restore via `database_backup.py`. Backend 8000, frontend strictPort 5173 (vite.config.ts).

## Verification
`.venv/Scripts/python.exe -m pytest -q` (40 passed), `npm run build --prefix frontend` (679kb bundle), `/docs` + `/openapi.json` expose new paths.
