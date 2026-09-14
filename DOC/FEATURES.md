# SIH 26103 — Feature Catalogue (updated 2026-09-14, 16-feature spec)

## 1 · Backend API (`/api`, FastAPI + SQLite)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Admin bearer token |
| POST | `/api/projects/upload` | CSV ingest (admin) |
| GET | `/api/projects` | List + filters |
| GET | `/api/projects/{id}` | Detail + derived features |
| GET | `/api/dashboard/summary` | Portfolio KPIs |
| GET | `/api/analytics/sectors` | Sector aggregates |
| GET | `/api/analytics/ministries` | Ministry aggregates |
| GET | `/api/analytics/benchmarks?project_id=` | Peer cohort |
| GET | `/api/risk/projects` | Risk alias list |
| GET | `/api/risk/projects/{id}` | Risk alias detail |
| GET | `/api/risk/projects/{id}/explanation` | SHAP drivers |
| GET | `/api/risk/projects/{id}/confidence` | **Feature 5** probability/confidence/data_quality/model_version/limitations |
| GET | `/api/risk/trends` | **Feature 2** history across snapshots, thresholds improving/stable/watch/deteriorating/rapid_deterioration, `risk-trends-v1` |
| GET | `/api/monitoring/snapshot-comparison` | Phase 2 portfolio deltas |
| GET | `/api/alerts` | Alerts |
| GET | `/api/datasets/{id}/quality` | Quality report |
| POST | `/api/assistant/query` | **Feature 16** 8 intents: rank_projects, explain_project, summarize_group, compare_peers, find_deteriorating_projects, list_early_warnings, show_priority, show_cost_drivers (grounded) |
| GET | `/api/datasets` | List datasets (for snapshot selectors) |
| GET | `/api/updates` | **Updates** filterable by category/search/date, paginated |
| GET | `/api/updates/{id}` | Update detail |
| GET | `/api/interventions/priority` | **Feature 3** weighted priority queue, `intervention-v1`, drivers list |
| GET | `/api/interventions/priority/{project_id}` | Single priority |
| GET | `/api/early-warnings` | **Feature 4** deterministic signals on scoring or read |
| GET | `/api/early-warnings/{id}` | Detail |
| POST | `/api/early-warnings/{id}/acknowledge` | Admin |
| POST | `/api/early-warnings/{id}/close` | Admin |
| GET | `/api/projects/{id}/progress-trajectory` | **Feature 6** expected vs actual, deviation |
| GET | `/api/risk/projects/{id}/forecast` | **Feature 7** historical + dashed linear-trend forecast |
| POST | `/api/simulation/project` | **Feature 8** read-only, never persists |
| GET | `/api/projects/{id}/recommendations` | **Feature 9** 1-5 rule actions |
| POST | `/api/reports/project-brief` | **Feature 10** 7-section brief |
| GET | `/api/analytics/cost-drivers` | **Feature 11** avg SHAP |
| GET | `/api/analytics/ministries/{ministry}/health` | **Feature 12** ministry health |
| GET | `/api/analytics/geography` | **Feature 13** region aggregates (illustrative) |
| GET | `/api/projects/{id}/timeline` | **Feature 14** snapshots across datasets |
| GET | `/api/ml/models` | **Feature 15** |
| GET | `/api/ml/models/{version}` | Detail |
| GET | `/api/ml/performance` | Metrics |

Filtering: dataset_id, sector, ministry, agency, risk_band, min_cost/max_cost, min_progress/max_progress, offset/limit (max 500). Pagination avoids N+1, server computes aggregates.

## 2 · Frontend (`frontend/src`)

| Route | Purpose |
|---|---|
| `/` | Home (hero, KPIs, map, sectors, risk charts, 3 latest live updates + View All → /updates) |
| `/dashboard` | 10-block hierarchy: KPIs, dataset, warnings, priority, trends, sectors, cost drivers, simulation teaser, chart, assistant |
| `/monitoring` | Monitoring overview (links to Changes, Warnings, Priority, Trends) |
| `/monitoring/changes` | Snapshot comparison |
| `/risk/trends` | Risk trends across snapshots |
| `/early-warnings` | Warning center |
| `/interventions` | Priority queue + bar chart |
| `/simulation` | What-if form (read-only) |
| `/projects` | Table |
| `/projects/:id` | 13-section investigation: facts, risk, confidence, trajectory, forecast, recommendations, SHAP, benchmark, timeline, priority, warnings, limitations, report |
| `/analytics` | Sectors, ministries, cost drivers, geography (illustrative map) |
| `/analytics/models` | Registry + performance |
| `/documents` | Docs + quality |
| `/updates` | Paginated updates (All/Dataset/Monitoring/Model/Methodology/Platform, search, featured + timeline) |
| `/updates/:id` | Update detail |
| `/help` | FAQs + health |

Shared shell: GovLayout with dropdown nav Home, Dashboard, Monitoring ▾ (Overview, Changes, Early Warnings, Intervention Priority, Risk Trends), Projects, Analytics ▾ (7 items), Simulation, Documents, Updates, Help; right side Login (secondary) + Sign Up (primary) 44px aligned, single-line nowrap typography; mobile grouped nav. Design tokens, Recharts with title/units/text alternative, loading/error/empty/unavailable, accessibility (skip link, 44px targets, focus, reduced-motion), mobile responsive.

Run: backend `python -m uvicorn backend.app.main:app --port 8000` (or `.venv/Scripts/python.exe -m uvicorn ...`), frontend `npm run dev --prefix frontend` (strictPort 5173). Docs at `/docs`, `/openapi.json`.
