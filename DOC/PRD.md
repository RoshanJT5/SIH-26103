# PRD.md — AI-Powered Infrastructure Project Monitoring & Early Warning System

## 1. Product Overview

**Problem Statement:** SIH 26103  
**Organization:** Ministry of Statistics and Programme Implementation (MoSPI)  
**Product Type:** AI/ML-powered web-based project-monitoring and decision-support platform

### Product Vision

Transform infrastructure project monitoring from a **descriptive reporting system** into an **explainable predictive and decision-support system** that helps officials identify risky projects early, understand the reasons behind the risk, and prioritize intervention.

### Product Statement

> Analyze project data, predict cost/time/implementation risk, explain the risk, and help monitoring officers decide which projects require attention first.

---

# 2. Background

MoSPI monitors large Central Sector infrastructure projects through the PAIMANA ecosystem.

The supplied project dataset contains project-level information such as:

- Project cost
- Revised cost
- Expenditure
- Physical progress
- Ministry
- Sector
- Implementing agency
- Original commissioning date
- Revised commissioning date
- Sanction date

The current MVP dataset is primarily a **snapshot** rather than a complete monthly time-series dataset.

Therefore, the first release focuses on **risk classification and decision support**. A future version can use historical monthly PAIMANA/OCMS records for genuine temporal early-warning forecasting.

---

# 3. Target Users

## Primary Users

### Monitoring Officers
Need to quickly identify projects requiring attention.

### Project Administrators
Need project-level insights and risk drivers.

### Policymakers / Senior Officials
Need portfolio-level summaries and sector/ministry comparisons.

### Analysts
Need project data, model outputs and benchmarking.

---

# 4. User Problems

### Problem 1 — Too many projects to manually inspect

Officials cannot manually analyze every project in a large portfolio.

**Solution:** Automatically rank projects by risk.

### Problem 2 — Problems are often visible only after they become serious

Traditional reports mainly describe current/project history.

**Solution:** Generate predictive risk indicators.

### Problem 3 — A risk score alone is not useful

An officer needs to know why a project is risky.

**Solution:** Explain model predictions using SHAP and measurable project indicators.

### Problem 4 — Difficult to prioritize intervention

Not every delayed/risky project has the same urgency.

**Solution:** Create risk bands and a priority queue.

### Problem 5 — Difficult to compare similar projects

**Solution:** Benchmark projects against similar sector/ministry/cost groups.

---

# 5. Goals

## Primary Goals

1. Build a centralized project-risk dashboard.
2. Predict cost-overrun risk.
3. Predict time-overrun risk.
4. Generate an overall project risk score.
5. Explain the major risk drivers.
6. Rank projects requiring attention.
7. Generate early-warning alerts.
8. Provide benchmarking and comparative analytics.

## Secondary Goals

1. Provide an LLM-based project intelligence assistant.
2. Support natural-language project queries.
3. Prepare the architecture for monthly data ingestion.
4. Keep the system based primarily on open-source software.

---

# 6. Non-Goals for MVP

The MVP will NOT:

- Automatically modify PAIMANA records.
- Make official policy decisions.
- Replace human monitoring officers.
- Claim guaranteed future project outcomes.
- Use an LLM as the primary prediction model.
- Automatically contact contractors/agencies.
- Invent missing project data.
- Treat model predictions as confirmed facts.

---

# 7. Core Product Modules

## Module A — Data Ingestion

### Requirements

- Upload CSV.
- Validate required columns.
- Detect missing/invalid records.
- Clean numeric fields.
- Parse dates.
- Detect duplicates.
- Produce data-quality statistics.

### Acceptance Criteria

- User can upload `Projects_Report.csv`.
- Invalid rows are flagged.
- Valid data becomes available to the dashboard.
- Data-quality errors are visible.

---

# 8. Module B — Project Portfolio Dashboard

The dashboard should show:

- Total projects
- High-risk projects
- Critical projects
- Average physical progress
- Total original cost
- Total revised cost
- Total expenditure
- Average cost escalation
- Average schedule delay

### Filters

- Sector
- Ministry
- Implementing agency
- Risk level
- Cost range
- Physical progress range

### Acceptance Criteria

Users can filter the portfolio and all dashboard metrics update accordingly.

---

# 9. Module C — Cost Risk Prediction

## Objective

Estimate the probability that a project is associated with cost-overrun risk.

### Output

```text
Cost Risk: 78%
Risk Level: HIGH
```

### Model

Primary:

- XGBoost / LightGBM

Baseline:

- Logistic Regression

### Important Rule

If the target is derived from:

```text
(Revised Cost - Original Cost) / Original Cost
```

then **Revised Cost cannot be used as an input feature for that predictive model**, because it causes data leakage.

For true future prediction, historical pre-outcome snapshots should be used.

---

# 10. Module D — Time Risk Prediction

## Objective

Estimate the probability of project schedule/time-overrun risk.

### Output

```text
Time Risk: 86%
Risk Level: CRITICAL
```

### Model

Primary:

- XGBoost / LightGBM

Baseline:

- Logistic Regression

### Important Rule

If the target is derived from the difference between original and revised commissioning dates, the revised date must not be used as a predictive input.

True future forecasting requires historical observations before the final outcome.

---

# 11. Module E — Project Risk Score

Create a normalized score from 0–100.

Prototype:

```text
Overall Risk =
0.40 × Cost Risk
+ 0.40 × Time Risk
+ 0.20 × Implementation Risk
```

The weights should be calibrated with validation data rather than treated as official policy.

### Risk Bands

| Score | Level |
|---:|---|
| 0–30 | Low |
| 31–60 | Medium |
| 61–80 | High |
| 81–100 | Critical |

---

# 12. Module F — Explainable AI

## Objective

Answer:

> Why is this project high risk?

Use SHAP for model-level and project-level explanations.

### Example

```text
Overall Risk: 84/100

Top contributing factors:
- Schedule deviation
- Low physical progress
- High expenditure ratio
- Project age
```

The UI should distinguish between:

- Model-derived drivers
- Direct project facts
- System recommendations

This prevents recommendations from being mistaken for factual observations.

---

# 13. Module G — Early Warning System

Generate alerts when risk crosses configured thresholds.

### Example

```text
🚨 CRITICAL PROJECT

Project X
Overall Risk: 87/100

Cost Risk: 79%
Time Risk: 92%

Key Drivers:
- Schedule deviation
- Low physical progress
- High expenditure relative to progress

Action:
Prioritize for detailed monitoring review.
```

### Alert levels

- Normal
- Watch
- High
- Critical

---

# 14. Module H — Project Detail

Each project should have a dedicated detail page.

### Information

- Project name
- Project code
- Sector
- Ministry
- Implementing agency
- Original cost
- Revised cost
- Expenditure
- Physical progress
- Original commissioning date
- Revised commissioning date
- Sanction date
- Cost risk
- Time risk
- Overall risk
- Risk level
- Risk drivers
- Recommended monitoring focus

---

# 15. Module I — Benchmarking

Allow users to compare a project with similar projects.

### Comparison Dimensions

- Sector
- Ministry
- Implementing agency
- Project-cost range

### Metrics

- Cost escalation
- Expenditure ratio
- Physical progress
- Schedule delay
- Risk score

### Example

> Project X has a higher risk score and lower physical progress than comparable Transport projects.

---

# 16. Module J — LLM Project Intelligence Assistant

The LLM is an optional intelligence interface over trusted data and model results.

### Example Queries

```text
Which projects are at highest risk?

Why is Project X high risk?

Show high-risk transport projects.

Which ministries have the highest average risk?

Compare Project A with similar projects.

What are the main risk drivers in the Energy sector?
```

### Required Architecture

```text
User Question
      ↓
LLM
      ↓
Intent / Query Extraction
      ↓
Project Database + Model Results
      ↓
Grounded Context
      ↓
LLM Response
```

The assistant must not answer from unsupported assumptions.

---

# 17. Key User Flows

## Flow 1 — Portfolio Monitoring

```text
Login
 ↓
Dashboard
 ↓
View risk distribution
 ↓
Filter sector/ministry
 ↓
View high-risk projects
 ↓
Open project
 ↓
Read risk explanation
 ↓
Prioritize monitoring
```

## Flow 2 — Project Investigation

```text
Select project
 ↓
Project details
 ↓
View cost/time risk
 ↓
View SHAP drivers
 ↓
View comparable projects
 ↓
View recommended monitoring focus
```

## Flow 3 — Natural Language

```text
Ask question
 ↓
LLM identifies intent
 ↓
Query trusted project/model data
 ↓
Generate grounded response
```

---

# 18. Data Model

Core project entity:

```text
Project
├── project_code
├── project_name
├── sector
├── ministry
├── implementing_agency
├── original_cost
├── revised_cost
├── expenditure
├── physical_progress
├── sanction_date
├── original_commissioning_date
├── revised_commissioning_date
├── derived_cost_overrun
├── derived_schedule_delay
├── cost_risk
├── time_risk
├── implementation_risk
├── overall_risk
└── risk_level
```

Future temporal model:

```text
Project
  └── MonthlySnapshot[]
        ├── month
        ├── expenditure
        ├── physical_progress
        ├── milestone_status
        └── other monthly indicators
```

---

# 19. API Requirements

### Data

```http
POST /api/projects/upload
GET  /api/projects
GET  /api/projects/{project_id}
```

### Analytics

```http
GET /api/dashboard/summary
GET /api/analytics/sectors
GET /api/analytics/ministries
GET /api/analytics/benchmarks
```

### Risk

```http
GET /api/risk/projects
GET /api/risk/projects/{project_id}
GET /api/risk/projects/{project_id}/explanation
```

### Assistant

```http
POST /api/assistant/query
```

---

# 20. Security & Reliability

For an MVP:

- Validate uploaded files.
- Sanitize inputs.
- Restrict administrative operations.
- Do not expose sensitive data unnecessarily.
- Log model version and prediction timestamp.
- Store model versions with prediction results.
- Show data freshness.
- Clearly label predictions as model outputs.
- Never allow the LLM to fabricate project information.

---

# 21. Success Metrics

### Product Metrics

- Time required to identify top-risk projects.
- Percentage of projects successfully processed.
- Dashboard response time.
- Number of actionable risk explanations.

### ML Metrics

- Precision
- Recall
- F1
- ROC-AUC
- PR-AUC
- Calibration

For an early-warning system, prioritize **recall for genuinely high-risk projects** while controlling false alerts.

---

# 22. MVP Acceptance Criteria

The MVP is complete when:

- [ ] CSV can be uploaded.
- [ ] Data quality is validated.
- [ ] Project portfolio is displayed.
- [ ] Cost-risk model works.
- [ ] Time-risk model works.
- [ ] Risk score is generated.
- [ ] Projects can be ranked.
- [ ] Risk explanations are shown.
- [ ] Dashboard supports filtering.
- [ ] Similar-project comparison works.
- [ ] Early-warning alerts are displayed.
- [ ] Model evaluation metrics are visible to the development/admin team.
- [ ] The system clearly communicates the snapshot-data limitation.

---

# 23. Future Roadmap

### Phase 1 — MVP

CSV → ML → Risk Score → SHAP → Dashboard

### Phase 2 — Predictive Monitoring

Historical monthly PAIMANA/OCMS data → temporal features → risk trajectories → early-warning forecasting.

### Phase 3 — Prescriptive Intelligence

Risk prediction → root-cause analysis → what-if analysis → intervention recommendations.

### Phase 4 — Integrated Platform

PAIMANA APIs → automated data ingestion → continuous model scoring → alerts → LLM assistant → reporting.

---

# 24. SIH Demo Story

The demo should show:

```text
Large Project Portfolio
        ↓
AI analyzes projects
        ↓
Top risky projects identified
        ↓
Cost + time risk calculated
        ↓
Risk explained with SHAP
        ↓
Similar projects compared
        ↓
Early warning generated
        ↓
Officer prioritizes intervention
```

### Core message

> **Don't just report that a project is delayed. Identify projects likely to face serious problems, explain the risk, and help officials decide where to intervene first.**
