# MVP.md — AI-Powered Infrastructure Project Monitoring & Early Warning System

## 1. Project Overview

**SIH Problem Statement:** 26103  
**Organization:** Ministry of Statistics and Programme Implementation (MoSPI)  
**Theme:** AI for Infrastructure Monitoring

### One-line MVP

An AI/ML-powered web platform that analyzes infrastructure project data, predicts **cost-overrun and time-overrun risk**, assigns an **overall project risk score**, explains major risk drivers, and helps monitoring officers prioritize projects for intervention.

---

## 2. Problem We Are Solving

PAIMANA contains information about large Central Sector infrastructure projects such as cost, expenditure, physical progress, ministries, sectors, implementing agencies and commissioning dates.

Existing monitoring can mainly answer:

> **What has already happened?**

Our system aims to answer:

> **Which projects are currently at risk, how serious is the risk, why is the project risky, and which projects should be monitored first?**

The MVP therefore moves from **descriptive monitoring → predictive and decision-support monitoring**.

---

## 3. Data Available for MVP

The supplied `Projects_Report.csv` contains project-level fields including:

- Sector Name
- Line Ministry
- Implementing Agency
- Project Code
- Project Name
- Original Cost
- Revised Cost
- Expenditure
- Physical Progress (%)
- Original Date of Commissioning
- Revised Date of Commissioning
- Sanction Date

### Important limitation

The supplied file is primarily a **project-level snapshot**, not a complete monthly time-series dataset.

Therefore, the MVP should not claim exact month-by-month future forecasting unless historical monthly observations are later added.

The first MVP should provide:

1. Current project risk assessment
2. Cost-overrun risk prediction
3. Time-overrun risk prediction
4. Risk ranking
5. Explainable risk drivers
6. Early-warning flags
7. Project comparison and analytics

With historical monthly PAIMANA/OCMS data, this can later become a true temporal early-warning system.

---

## 4. MVP Goals

### Primary

- Identify projects with high cost-overrun risk.
- Identify projects with high time-overrun risk.
- Generate a project-level risk score from 0–100.
- Rank projects requiring attention.
- Explain why a project is classified as high risk.
- Provide a simple dashboard for monitoring officials.

### Secondary

- Compare project performance across sectors, ministries and agencies.
- Show cost and schedule deviation indicators.
- Provide basic recommended monitoring actions.
- Add an LLM-based project assistant if time permits.

---

## 5. Proposed Architecture

```text
                  Projects_Report.csv
                          |
                          v
                  Data Cleaning Layer
                          |
                          v
                 Feature Engineering
                          |
             +------------+------------+
             |                         |
             v                         v
     Cost Overrun Model        Time Overrun Model
       XGBoost/LightGBM          XGBoost/LightGBM
             |                         |
             +------------+------------+
                          |
                          v
                   Risk Score Engine
                          |
                          v
                  Explainable AI
                       (SHAP)
                          |
                          v
                Early Warning Engine
                          |
             +------------+------------+
             |                         |
             v                         v
       Web Dashboard             LLM Assistant
```

---

## 6. Data Processing

### Cleaning

- Remove duplicate project records.
- Standardize column names.
- Convert cost/expenditure fields to numeric.
- Parse dates consistently.
- Handle missing values.
- Detect impossible values such as progress > 100%.
- Identify missing revised cost/date values.
- Produce a data-quality report.

### Feature Engineering

Create derived variables such as:

```text
Cost Overrun % =
(Revised Cost - Original Cost) / Original Cost × 100
```

```text
Expenditure Ratio =
Expenditure / Revised Cost
```

```text
Cost Increase =
Revised Cost - Original Cost
```

```text
Schedule Delay =
Revised Commissioning Date - Original Commissioning Date
```

```text
Project Age =
Current Date - Sanction Date
```

Also use:

- Physical Progress
- Sector
- Ministry
- Implementing Agency

If reliable historical progress data is unavailable, do not invent an expected-progress value.

---

## 7. Prediction Strategy

### 7.1 Cost Overrun Model

Target:

```text
1 = Cost overrun
0 = No cost overrun
```

For a richer version:

```text
Low       = 0–10%
Medium    = 10–20%
High      = >20%
```

Models:

- **Baseline:** Logistic Regression
- **Main:** XGBoost or LightGBM

Output:

```text
Cost Overrun Probability: 78%
Risk Level: HIGH
```

### 7.2 Time Overrun Model

Target:

```text
1 = Time overrun
0 = No time overrun
```

Delay duration can be calculated as:

```text
Revised Commissioning Date
-
Original Commissioning Date
```

Models:

- **Baseline:** Logistic Regression
- **Main:** XGBoost or LightGBM

Output:

```text
Time Overrun Probability: 86%
Risk Level: HIGH
```

---

## 8. Critical Data-Leakage Rule

Do **not** use variables that directly reveal the target.

For cost-overrun prediction, do not use **Revised Cost** if the target is calculated from Revised Cost.

For time-overrun prediction, do not use **Revised Commissioning Date** if the target is calculated from the revised date.

Otherwise, the model will appear highly accurate while learning the answer directly.

### Preferred training data

For genuine prediction, use historical snapshots:

```text
Project A — Month 1
Project A — Month 2
Project A — Month 3
...
Project A — Final outcome
```

If only the supplied snapshot is available, present the model as a **risk classification / analytical prototype**, not a validated future forecasting model.

---

## 9. Overall Risk Score

A simple prototype can combine model outputs and operational indicators:

```text
Overall Risk Score =
0.40 × Cost Risk
+ 0.40 × Time Risk
+ 0.20 × Implementation Risk
```

The weights should ultimately be calibrated using validation data and stakeholder requirements.

Example risk bands:

```text
0–30    → LOW
31–60   → MEDIUM
61–80   → HIGH
81–100  → CRITICAL
```

---

## 10. Explainable AI

Use **SHAP** to answer:

> Why did the model classify this project as high risk?

Example:

```text
Project Risk Score: 84 / 100

Top Risk Drivers:
+22  Schedule deviation
+18  Low physical progress
+15  High expenditure ratio
+11  Project age
 +8  Sector-level historical risk
```

The actual contribution values must come from the trained model rather than being manually assigned.

This is important because officials should receive an explanation instead of a black-box score.

---

## 11. Early Warning Engine

Convert predictions into actionable alerts.

Example:

```text
🚨 CRITICAL PROJECT

Project: Highway Development Project X

Overall Risk: 87/100
Cost Risk: 79%
Time Risk: 92%

Key Drivers:
- Significant schedule deviation
- Low physical progress
- High expenditure relative to progress

Recommended Review:
Prioritize the project for detailed implementation review.
```

Alert levels:

- 🟢 Normal
- 🟡 Watch
- 🟠 High Risk
- 🔴 Critical

---

## 12. Dashboard

### Executive Dashboard

Display:

- Total projects
- High-risk projects
- Critical projects
- Average cost overrun
- Average time overrun
- Total original cost
- Total revised cost
- Total expenditure
- Projects requiring attention

### Analytics

Charts:

- Risk by sector
- Risk by ministry
- Risk by implementing agency
- Cost-risk distribution
- Time-risk distribution

### Project Ranking

| Project | Sector | Cost Risk | Time Risk | Overall Risk | Status |
|---|---|---:|---:|---:|---|
| Project A | Transport | 82% | 91% | 88 | Critical |
| Project B | Energy | 63% | 72% | 68 | High |
| Project C | Water | 24% | 38% | 31 | Low |

### Project Detail

Show:

- Project name/code
- Ministry
- Sector
- Implementing agency
- Original cost
- Revised cost
- Expenditure
- Physical progress
- Original commissioning date
- Revised commissioning date
- Cost-risk probability
- Time-risk probability
- Overall risk score
- Risk level
- Top SHAP drivers
- Suggested monitoring action

---

## 13. Benchmarking Module

Allow an officer to compare a project with similar projects.

Example:

```text
Selected Project:
Transport Project X

Compare against:
- Same sector
- Same ministry
- Similar project-cost range
```

Show:

- Average cost overrun
- Average delay
- Physical progress
- Expenditure ratio
- Risk score

This answers:

> **Is this project performing worse than similar projects?**

---

## 14. LLM Project Intelligence Assistant

The LLM should be an optional layer, not the prediction engine.

Example questions:

```text
Which projects are at highest risk?

Why is Project X high risk?

Show high-risk transport projects.

Which ministries have the highest average project risk?

Compare Project A with similar projects.

What are the main risk drivers in this sector?
```

Recommended flow:

```text
User Question
     ↓
LLM
     ↓
Structured Query / Retrieval
     ↓
Project Database + Model Results
     ↓
Grounded LLM Response
```

The LLM must not invent project facts. Answers should be grounded in the project database and model outputs.

---

## 15. Recommended Technology Stack

### Backend

- Python
- FastAPI

### Data

- Pandas
- NumPy
- Scikit-learn

### Machine Learning

- XGBoost
- LightGBM
- Scikit-learn

### Explainability

- SHAP

### Database

- PostgreSQL
- SQLite for a quick prototype

### Frontend

For the fastest MVP:

- Streamlit

For a production-style UI:

- React
- Tailwind CSS
- Recharts/Plotly

### LLM

Use an open-source model where possible:

- Llama
- Qwen
- Mistral

Use retrieval/tool-based access so the LLM answers from actual project data.

### Deployment

- Docker
- Linux/cloud environment

---

## 16. Model Evaluation

Compare:

```text
Logistic Regression
        VS
XGBoost / LightGBM
```

Evaluate using:

- Precision
- Recall
- F1-score
- ROC-AUC
- PR-AUC where class imbalance exists
- Confusion matrix
- Calibration
- Early-warning lead time when temporal data is available

Do not report only accuracy.

If only 10% of projects are risky, a model predicting "not risky" for every project could achieve 90% accuracy while being useless.

For an early-warning system, **recall for high-risk projects** is especially important.

---

## 17. MVP Scope vs Future Scope

### MVP — Build This

1. CSV ingestion
2. Data cleaning
3. Feature engineering
4. Cost-risk model
5. Time-risk model
6. Overall risk score
7. SHAP explanations
8. Risk ranking
9. Early-warning alerts
10. Dashboard
11. Sector/ministry benchmarking

### Phase 2

1. Historical monthly PAIMANA/OCMS data
2. True time-series forecasting
3. Project risk trend
4. Risk trajectory
5. Monthly automated alerts
6. Contractor/land/environment/legal variables
7. Survival/time-to-event models

### Phase 3

1. LLM project assistant
2. Natural-language analytics
3. Automated monitoring reports
4. What-if scenario analysis
5. Prescriptive intervention recommendations
6. API integration with PAIMANA

---

## 18. SIH Differentiator

Do not present the project as:

> **"We made an AI dashboard."**

Present it as:

> **"We built an explainable AI decision-support system that identifies infrastructure projects requiring intervention before risks become severe."**

The five-layer story:

```text
1. MONITOR
   What is happening?

2. PREDICT
   What is likely to happen?

3. EXPLAIN
   Why is it likely to happen?

4. PRIORITIZE
   Which projects need attention first?

5. ACT
   What should the monitoring officer investigate?
```

---

## 19. Example End-to-End Scenario

### Input

```text
Project: National Highway X

Original Cost: ₹2,000 Cr
Revised Cost: ₹2,350 Cr
Expenditure: ₹1,700 Cr
Physical Progress: 52%
Original Completion: 2025
Revised Completion: 2027
Sector: Transport
```

### System Output

```text
Cost Risk        → HIGH
Time Risk        → CRITICAL
Overall Risk     → 86/100
```

### Explanation

```text
Major contributing factors:
- Significant schedule revision
- High expenditure ratio
- Physical progress not keeping pace
- Cost escalation
```

### Action

```text
🚨 Prioritize for monitoring review.

Suggested focus:
1. Investigate schedule bottlenecks.
2. Review expenditure versus physical progress.
3. Check reasons for cost escalation.
4. Review implementing agency/contractor status.
```

---

## 20. Final MVP Definition

The MVP is successful if a government monitoring officer can:

1. Load project data.
2. See the complete project portfolio.
3. Identify high-risk projects immediately.
4. View cost and time risk probabilities.
5. Understand why a project is risky.
6. Filter projects by sector/ministry/agency.
7. Compare similar projects.
8. Open a project and inspect its details.
9. Receive an early-warning alert.
10. Use the output to prioritize monitoring.

### Core MVP Formula

```text
PAIMANA Project Data
        +
Feature Engineering
        +
Statistical Baseline
        +
XGBoost/LightGBM
        +
SHAP Explainability
        +
Risk Scoring
        +
Early Warning
        +
Dashboard
        =
AI-Powered Infrastructure Monitoring MVP
```

---

## 21. Important SIH Presentation Caveat

The supplied `Projects_Report.csv` is a project-level snapshot. A genuine **future early-warning prediction system** should ideally be trained on historical monthly project observations from OCMS/PAIMANA.

Therefore, present the current MVP honestly as:

> **"A prototype predictive risk-classification and early-warning framework using the currently available project-level data, designed to become a true temporal forecasting system when historical monthly records are integrated."**

This is stronger than pretending that a single snapshot can prove future forecasting accuracy.
