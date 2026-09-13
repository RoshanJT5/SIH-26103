# TECHSTACK.md — AI-Powered Infrastructure Project Monitoring

## 1. Recommended Stack

The recommended architecture is intentionally **open-source first**, lightweight for an SIH MVP, and scalable toward a production deployment.

```text
Frontend
React + TypeScript + Tailwind CSS
        ↓
Backend API
FastAPI + Python
        ↓
Data Layer
PostgreSQL
        ↓
ML Layer
Scikit-learn + XGBoost/LightGBM
        ↓
Explainability
SHAP
        ↓
LLM/RAG Layer
Open-source LLM + Retrieval
        ↓
Deployment
Docker + Linux
```

For the fastest hackathon prototype, **Streamlit can replace React + FastAPI** initially.

---

# 2. Frontend

## Recommended

- React
- TypeScript
- Tailwind CSS
- Recharts or Plotly

### Why?

The dashboard needs:

- Interactive filters
- Risk cards
- Tables
- Charts
- Project detail pages
- Risk explanations
- Responsive UI

### MVP Alternative

**Streamlit**

Use Streamlit if the team has limited frontend development time.

Recommended strategy:

```text
Hackathon MVP:
Streamlit

Production-style demo:
React + TypeScript
```

---

# 3. Backend

## FastAPI

Use:

- Python
- FastAPI
- Pydantic
- Uvicorn

### Responsibilities

- File upload
- Data validation
- Project APIs
- Dashboard APIs
- Prediction APIs
- Benchmarking
- LLM assistant endpoint

Example:

```text
POST /api/projects/upload
GET  /api/projects
GET  /api/dashboard/summary
GET  /api/risk/projects
GET  /api/risk/projects/{id}
POST /api/assistant/query
```

---

# 4. Data Processing

## Pandas

Use Pandas for:

- CSV loading
- Cleaning
- Missing-value handling
- Type conversion
- Date parsing
- Feature engineering
- Aggregations

## NumPy

Use NumPy for:

- Numerical operations
- Array processing
- Model preprocessing

## Scikit-learn

Use for:

- Preprocessing
- Encoding
- Train/test splitting
- Baseline models
- Metrics
- Pipelines
- Calibration

---

# 5. Machine Learning

## Primary Recommendation

### XGBoost

Best candidate for the initial structured-data model.

Use it for:

- Cost-risk classification
- Time-risk classification
- Risk probability

### Alternative

### LightGBM

Useful if the dataset becomes much larger.

### Baseline

### Logistic Regression

This is important for SIH because the problem explicitly asks whether ML provides meaningful gains over conventional statistical methods.

Comparison:

```text
Logistic Regression
        VS
XGBoost
```

Report:

- Precision
- Recall
- F1
- ROC-AUC
- PR-AUC
- Calibration

---

# 6. Explainable AI

## SHAP

Use SHAP to explain:

- Global feature importance
- Individual project predictions
- Risk drivers

Example UI:

```text
Overall Risk: 84

Main Drivers
─────────────
Schedule deviation     ↑
Physical progress      ↓
Expenditure ratio      ↑
Project age            ↑
```

Avoid manually assigning explanation weights. Explanations should come from the trained model.

---

# 7. Database

## PostgreSQL

Recommended for the production-style MVP.

### Main tables

```text
projects
risk_predictions
risk_explanations
model_versions
monthly_snapshots   # future
alerts              # future
```

### Why PostgreSQL?

- Open source
- Reliable
- Good filtering/aggregation
- Easy FastAPI integration
- Suitable for future growth

### Quick Prototype

SQLite is acceptable for a local demo.

---

# 8. LLM Layer

The LLM is **not** the core prediction model.

Use the LLM for:

- Natural-language queries
- Project explanations
- Portfolio summaries
- Comparative questions
- Report generation

### Example

User:

> Why is Project X high risk?

System:

```text
LLM
 ↓
Retrieve Project X
 ↓
Retrieve prediction + SHAP results
 ↓
Generate grounded explanation
```

---

# 9. RAG / Retrieval

For the MVP, use structured retrieval first.

### Sources

- Project database
- Risk predictions
- SHAP explanations
- Benchmarking results

### Future sources

- PAIMANA documentation
- Project reports
- Monthly monitoring reports
- Government documents
- Project notes

### Important

The assistant should answer only from retrieved/trusted context when making project-specific claims.

---

# 10. Open-Source LLM Options

Potential choices:

- Llama
- Qwen
- Mistral

The exact model should be selected based on:

- Hardware available
- Context size
- Indian-language requirements
- Response speed
- License suitability
- Quantization support

For an SIH demo, a smaller quantized model may be more practical than a very large model.

---

# 11. ML Pipeline

```text
Raw CSV
   ↓
Validation
   ↓
Cleaning
   ↓
Feature Engineering
   ↓
Train/Validation Split
   ↓
Baseline Model
   ↓
XGBoost/LightGBM
   ↓
Evaluation
   ↓
Calibration
   ↓
SHAP
   ↓
Model Registry
   ↓
Prediction API
```

---

# 12. Feature Engineering

Potential features:

```text
cost_increase
cost_overrun_percentage
expenditure_ratio
project_age
schedule_delay_days
physical_progress
sector
ministry
implementing_agency
```

### Important

Features that directly reveal the target must not be used for prediction.

For example:

```text
Target:
Cost Overrun

Do NOT use:
Revised Cost
```

when revised cost itself defines the target.

Similarly:

```text
Target:
Time Overrun

Do NOT use:
Revised Commissioning Date
```

when the target is derived from that date.

---

# 13. Model Training Strategy

## If only snapshot data is available

Use the dataset primarily for:

- Descriptive analytics
- Risk classification prototype
- Pattern discovery
- Benchmarking

Be careful about claiming future prediction.

## If historical monthly data becomes available

Use:

- Lag features
- Rolling averages
- Progress velocity
- Expenditure velocity
- Milestone slippage
- Schedule trajectory

Then evaluate with **time-based splits**, not random splits.

Example:

```text
Train:
2021–2024

Validation:
2025

Test:
2026
```

This better represents real deployment.

---

# 14. Risk Engine

Inputs:

```text
Cost Risk
Time Risk
Implementation Risk
```

Output:

```text
Overall Risk Score
Risk Level
Priority
```

Prototype:

```text
Risk =
0.40 Cost Risk
+ 0.40 Time Risk
+ 0.20 Implementation Risk
```

The weighting should later be validated.

---

# 15. Visualization

Recommended charts:

### Portfolio

- Risk distribution
- Projects by sector
- Projects by ministry
- Cost escalation
- Expenditure distribution

### Risk

- Risk matrix
- Cost-risk vs time-risk scatter plot
- Top 10 risky projects
- Sector risk comparison

### Project

- Cost vs expenditure
- Physical progress
- Schedule information
- SHAP explanation

---

# 16. Deployment

## Containerization

Use:

- Docker
- Docker Compose

Possible services:

```text
frontend
backend
postgres
ml-service
llm-service
```

For the simplest MVP:

```text
streamlit
postgres
```

may be enough.

---

# 17. Suggested Repository Structure

```text
project-monitoring/
│
├── frontend/
│   ├── src/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── services/
│   │   └── schemas/
│   └── requirements.txt
│
├── ml/
│   ├── data/
│   ├── notebooks/
│   ├── features/
│   ├── training/
│   ├── evaluation/
│   └── models/
│
├── llm/
│   ├── retrieval/
│   ├── prompts/
│   └── assistant/
│
├── database/
│   └── migrations/
│
├── tests/
│
├── docker/
│
├── README.md
├── MVP.md
├── PRD.md
└── TECHSTACK.md
```

---

# 18. Development Priority

## Priority 1 — Must Build

```text
CSV ingestion
      ↓
Data cleaning
      ↓
Feature engineering
      ↓
ML models
      ↓
Risk score
      ↓
SHAP
      ↓
Dashboard
```

## Priority 2 — Strong SIH Features

```text
Benchmarking
Early warnings
Risk ranking
Project detail
```

## Priority 3 — Differentiators

```text
LLM assistant
RAG
Prescriptive recommendations
Scenario analysis
```

Do not sacrifice the ML pipeline and explainability just to add an LLM chatbot.

---

# 19. Performance Targets for MVP

These are engineering targets, not official MoSPI requirements.

- CSV processing: < 10 seconds for a few thousand projects
- Dashboard load: < 3 seconds after data is loaded
- Prediction generation: near real-time for a project
- API availability: > 99% in a deployed demo environment
- LLM response: ideally < 10 seconds depending on model/hardware

---

# 20. Security

Implement:

- File type validation
- Input sanitization
- Authentication for admin operations
- Role-based access for future deployment
- API authentication
- Secure database credentials
- No secrets in source code
- Audit logging
- Model/version tracking

---

# 21. Observability

Track:

- Data ingestion timestamp
- Dataset version
- Model version
- Prediction timestamp
- API errors
- LLM requests
- Model performance
- Alert generation

Every prediction should be traceable to:

```text
Dataset Version
+
Model Version
+
Prediction Timestamp
```

---

# 22. Future Upgrade Path

### Current

```text
Snapshot CSV
    ↓
Tabular ML
    ↓
Risk Score
```

### Future

```text
Monthly PAIMANA Data
        ↓
Time-Series Features
        ↓
Temporal ML / Survival Models
        ↓
Risk Trajectory
        ↓
Early Warning
```

### Advanced

```text
Structured Data
+
Documents
+
Historical Trends
+
External Risk Variables
        ↓
Multimodal Project Intelligence
```

---

# 23. Recommended Final Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Tailwind |
| Fast MVP UI | Streamlit |
| Backend | FastAPI |
| Language | Python |
| Data Processing | Pandas + NumPy |
| ML | XGBoost + Scikit-learn |
| Alternative ML | LightGBM |
| Explainability | SHAP |
| Database | PostgreSQL |
| Charts | Recharts / Plotly |
| LLM | Llama / Qwen / Mistral |
| Retrieval | Structured DB retrieval + RAG for documents |
| Containers | Docker |
| API Server | Uvicorn |
| Testing | Pytest |
| Version Control | Git + GitHub |
| Deployment | Docker/Linux/cloud |

---

# 24. Architecture Principle

The most important architectural decision is:

> **Use ML for prediction, SHAP for explanation, database retrieval for facts, and LLM for interaction.**

Do not use the LLM to predict project risk when a structured ML model can do it more reliably and measurably.
