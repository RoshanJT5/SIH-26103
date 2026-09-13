# Approach.md — SIH 26103 AI-Powered Infrastructure Monitoring

## 1. Our Core Approach

We will build an **Explainable AI-based Project Risk Intelligence Platform**.

The system will not simply display project data. It will:

```text
Understand
   ↓
Analyze
   ↓
Predict
   ↓
Explain
   ↓
Prioritize
   ↓
Recommend
```

### Core idea

> **For every infrastructure project, estimate the probability of cost/time problems, explain the major risk factors, rank projects by urgency, and provide actionable monitoring insights.**

---

# 2. Why This Approach?

The problem statement asks for a shift from:

```text
Descriptive Monitoring
"What has happened?"
```

to:

```text
Predictive Monitoring
"What is likely to happen?"
```

and ultimately:

```text
Prescriptive Monitoring
"What should we investigate/do?"
```

Therefore, our architecture has three major intelligence layers:

### Layer 1 — Predict

Machine Learning predicts project risks.

### Layer 2 — Explain

Explainable AI identifies the factors contributing to the prediction.

### Layer 3 — Recommend

A rule/model-based decision layer converts the risk into suggested monitoring actions.

---

# 3. High-Level System Flow

```text
             PAIMANA / OCMS Data
                      |
                      v
              Data Ingestion
                      |
                      v
             Data Quality Check
                      |
                      v
             Feature Engineering
                      |
          +-----------+-----------+
          |                       |
          v                       v
   Cost Risk Model         Time Risk Model
    XGBoost/LightGBM        XGBoost/LightGBM
          |                       |
          +-----------+-----------+
                      |
                      v
              Risk Score Engine
                      |
                      v
                SHAP Explainability
                      |
                      v
              Early Warning Engine
                      |
                      v
             Recommendation Layer
                      |
          +-----------+-----------+
          |                       |
          v                       v
     Web Dashboard          LLM Assistant
```

---

# 4. Step 1 — Understand the Data

The supplied `Projects_Report.csv` contains project-level information such as:

- Project Code
- Project Name
- Sector
- Line Ministry
- Implementing Agency
- Original Cost
- Revised Cost
- Expenditure
- Physical Progress
- Original Commissioning Date
- Revised Commissioning Date
- Sanction Date

First, we perform a complete data-quality assessment.

### Questions to answer

- How many projects are present?
- Which columns have missing values?
- Are there duplicate projects?
- Are costs stored consistently?
- Are dates valid?
- Are physical-progress values between 0 and 100?
- Which sectors have the most projects?
- Which ministries have the largest portfolio?
- How many projects show observed cost escalation?
- How many show observed schedule revision?

This stage creates the foundation for all subsequent modeling.

---

# 5. Step 2 — Data Cleaning

The pipeline will:

```text
Raw CSV
  ↓
Remove duplicates
  ↓
Normalize column names
  ↓
Convert numeric fields
  ↓
Parse dates
  ↓
Handle missing values
  ↓
Validate ranges
  ↓
Create clean dataset
```

### Example

If:

```text
Physical Progress = "55%"
```

convert it to:

```text
55.0
```

If:

```text
Original Cost = "₹2,500 Cr"
```

convert it into a numeric representation suitable for analysis.

Invalid values should be flagged rather than silently changed.

---

# 6. Step 3 — Feature Engineering

Raw project fields are converted into meaningful analytical features.

## Cost Features

```text
Cost Increase
Cost Escalation %
Expenditure Ratio
Remaining Cost
```

Example:

```text
Original Cost = ₹1,000 Cr
Revised Cost = ₹1,200 Cr

Cost Escalation = 20%
```

---

## Schedule Features

```text
Schedule Revision Days
Project Age
Planned Duration
```

Example:

```text
Original Completion = 2025
Revised Completion = 2027

Schedule Revision = approximately 2 years
```

---

## Progress Features

Use:

```text
Physical Progress
Expenditure Ratio
Progress-to-Expenditure Relationship
```

A potentially important warning pattern is:

```text
High expenditure
+
Low physical progress
=
Possible implementation inefficiency
```

This should be treated as an analytical signal, not automatically as proof of a problem.

---

# 7. Step 4 — Define Prediction Targets Carefully

This is one of the most important parts of the project.

## Cost Risk Target

A possible target:

```text
Cost Overrun = 1
if cost escalation exceeds selected threshold
```

Example:

```text
0% → No Overrun
>0% → Overrun
```

or a more useful classification:

```text
Low      → 0–10%
Medium   → 10–20%
High     → >20%
```

The final threshold should be selected after examining the actual data distribution.

---

## Time Risk Target

Similarly:

```text
Time Overrun = 1
if revised completion is later than original completion
```

or classify delay into meaningful categories.

---

# 8. Critical Issue — Data Leakage

We must avoid using the answer as an input to predict the answer.

### Example

If:

```text
Cost Overrun =
(Revised Cost - Original Cost) / Original Cost
```

then **Revised Cost must not be used as a feature for the cost-overrun prediction model**.

Otherwise:

```text
Model sees Revised Cost
       ↓
Target is directly calculable
       ↓
Artificially high accuracy
```

The same applies to:

```text
Revised Commissioning Date
```

when predicting time overrun derived from that date.

---

# 9. Step 5 — Statistical Baseline

Before claiming that AI/ML is better, build a conventional baseline.

### Baseline model

**Logistic Regression**

This gives us a reference point.

Then compare:

```text
Logistic Regression
       VS
XGBoost / LightGBM
```

This directly addresses one of the technical dimensions in the SIH problem statement.

---

# 10. Step 6 — Machine Learning Models

## Main Model: XGBoost

Use XGBoost for structured/tabular project data.

Why?

- Handles nonlinear relationships.
- Works well with mixed project features.
- Good performance on tabular data.
- Provides probabilities.
- Works well with SHAP.
- Easier to explain than many deep-learning architectures.

## Alternative

LightGBM can be tested as a second tree-based model.

---

# 11. Step 7 — Cost Risk Prediction

The model receives project characteristics and outputs:

```text
Cost Overrun Probability
```

Example:

```text
Project A

Cost Risk = 78%
Risk Band = HIGH
```

The system should not say:

> "This project will definitely exceed cost."

It should say:

> "The model estimates a 78% probability of the defined cost-risk outcome."

This is more scientifically correct.

---

# 12. Step 8 — Time Risk Prediction

Similarly:

```text
Project A

Time Risk = 86%
Risk Band = CRITICAL
```

The output represents model-estimated risk according to the target definition.

---

# 13. Step 9 — Implementation Risk

Implementation risk can combine operational indicators such as:

- Physical progress
- Expenditure ratio
- Schedule indicators
- Project age
- Sector/agency patterns

Initially, this can be a transparent scoring framework.

The implementation rule is versioned as `risk-rules-v1` for the MVP. It scores
only observed values and does not infer expected progress: low physical progress
(0-25%) contributes 40 points, moderate progress (greater than 25% through 50%)
contributes 20, expenditure ahead of progress by at least 25 percentage points
contributes 35, and a gap of at least 10 points contributes 17.5. Schedule
revision contributes 25 points at 365 or more days, 17.5 at 180-364 days, and
10 at 90-179 days. Missing indicators are omitted and the available points are
renormalized; if every indicator is missing, implementation risk is unavailable.

Component probabilities are converted to percentages before blending:
`0.40 * cost + 0.40 * time + 0.20 * implementation`. The continuous bands are
Low `[0,30]`, Medium `(30,60]`, High `(60,80]`, and Critical `(80,100]`.
Missing cost, time, or implementation components make the overall risk
unavailable. Initial alerts are deduplicated by snapshot, rule version, and
band; a threshold-crossing alert is emitted only when a comparable prior
observation moves into a higher band. Benchmark percentiles require at least
10 comparable peers after excluding the subject project.

Example:

```text
Progress concern
      +
Expenditure/progress mismatch
      +
Schedule concern
      =
Implementation Risk
```

As historical monthly data becomes available, this can be replaced or enhanced with a trained ML model.

---

# 14. Step 10 — Overall Risk Score

Combine the individual risk dimensions.

Prototype:

```text
Overall Risk =
40% Cost Risk
+
40% Time Risk
+
20% Implementation Risk
```

Example:

```text
Cost Risk           = 78
Time Risk           = 86
Implementation Risk = 72

Overall Risk ≈ 80
```

The weights should eventually be validated using historical outcomes and stakeholder feedback.

---

# 15. Step 11 — Risk Classification

Convert the score into understandable categories.

```text
0–30    → LOW
31–60   → MEDIUM
61–80   → HIGH
81–100  → CRITICAL
```

Example:

```text
Risk Score = 84

Status = CRITICAL
```

Thresholds should be calibrated rather than assumed to be official government thresholds.

---

# 16. Step 12 — Explainable AI

A government officer needs more than:

> "Risk = 84"

They need:

> "Why?"

Therefore, use **SHAP**.

Example:

```text
Project Risk = 84

Major Risk Drivers:

1. Schedule deviation
2. Low physical progress
3. High expenditure ratio
4. Long project age
```

The dashboard can visualize these drivers.

---

# 17. Step 13 — Early Warning System

The risk engine continuously identifies projects crossing risk thresholds.

Example:

```text
                    Project Portfolio
                           |
                           v
                     Risk Scoring
                           |
             +-------------+-------------+
             |             |             |
           LOW          MEDIUM        HIGH/CRITICAL
             |             |             |
         Normal         Watch          ALERT
```

### Alert Example

```text
🚨 HIGH-RISK PROJECT

Project: Highway Project X

Overall Risk: 87/100
Cost Risk: 79%
Time Risk: 92%

Key Signals:
- Schedule revision
- Low physical progress
- High expenditure ratio

Priority:
Immediate detailed monitoring review
```

---

# 18. Step 14 — Prescriptive Recommendation Layer

The system should convert identified risk patterns into **monitoring suggestions**, not autonomous government decisions.

Example:

```text
Risk:
High time-overrun probability

Observed signals:
Schedule revision + low progress

Suggested monitoring focus:
Review milestone bottlenecks and implementation status.
```

Another example:

```text
Risk:
High cost-overrun probability

Observed signals:
Large cost escalation + high expenditure

Suggested monitoring focus:
Review causes of cost escalation and expenditure progression.
```

Recommendations should be presented as:

> **Suggested monitoring focus**

rather than:

> **AI decision**

because final decisions belong to authorized officials.

---

# 19. Step 15 — Benchmarking

A project becomes more meaningful when compared with similar projects.

Example:

```text
Project X
    |
    +---- Same sector
    +---- Similar project size
    +---- Same ministry
```

Compare:

- Cost escalation
- Physical progress
- Expenditure ratio
- Schedule indicators
- Risk score

Output:

> Project X is in the top 10% of risk among comparable projects.

This percentile should only be calculated when enough comparable projects exist.

---

# 20. Step 16 — Dashboard

The dashboard is the main user interface.

## Executive View

```text
-----------------------------------------
Infrastructure Risk Dashboard
-----------------------------------------

Total Projects       1,775

Critical             XXX
High                 XXX
Medium               XXX
Low                  XXX

Total Original Cost  ₹XXX
Total Revised Cost   ₹XXX
Total Expenditure    ₹XXX
-----------------------------------------
```

## Risk Map

Show:

```text
Cost Risk  vs  Time Risk
```

Projects in the top-right corner are high on both dimensions.

---

# 21. Project Detail Page

When an officer clicks a project:

```text
Project X
────────────────────────────

Sector: Transport
Ministry: XXXXX
Agency: XXXXX

Original Cost: ₹XXXX Cr
Revised Cost: ₹XXXX Cr
Expenditure: ₹XXXX Cr

Physical Progress: XX%

Cost Risk: XX%
Time Risk: XX%
Overall Risk: XX/100

Risk Level: HIGH
```

Then:

```text
WHY?

1. Schedule signal
2. Progress signal
3. Expenditure signal
```

Then:

```text
Suggested Monitoring Focus

→ Review delayed milestones
→ Review expenditure vs progress
→ Investigate reported implementation bottlenecks
```

---

# 22. Step 17 — LLM Assistant

The LLM is an **interface**, not the prediction engine.

### Example

User:

> Show me the top 10 high-risk transport projects.

System:

```text
User Question
      ↓
LLM identifies request
      ↓
Query project/risk database
      ↓
Retrieve results
      ↓
LLM formats grounded response
```

### Another query

> Why is Project X risky?

The LLM retrieves:

- Project data
- Model probabilities
- SHAP drivers
- Benchmarking results

and produces a concise explanation.

---

# 23. RAG Strategy

For project-specific answers:

```text
Question
   ↓
Retrieve trusted data
   ↓
Project record
   +
Risk prediction
   +
SHAP explanation
   +
Benchmark data
   ↓
LLM
   ↓
Answer
```

For future document intelligence:

```text
Question
   ↓
Hybrid Retrieval
   ↓
PAIMANA data + project reports + documents
   ↓
LLM
   ↓
Grounded answer
```

The LLM should never be allowed to invent missing project information.

---

# 24. Model Evaluation Strategy

We will evaluate models using:

- Precision
- Recall
- F1-score
- ROC-AUC
- PR-AUC
- Confusion matrix
- Calibration

### Most important

For an early-warning system:

> **Recall for genuinely risky projects is especially important.**

Missing a truly high-risk project can be more harmful than generating an additional review alert.

However, excessive false positives also create alert fatigue, so precision must be monitored too.

---

# 25. If Historical Monthly Data Becomes Available

This is the most important future improvement.

Current:

```text
One project snapshot
       ↓
Risk classification
```

Future:

```text
Project X

Jan → progress 20%
Feb → progress 25%
Mar → progress 27%
Apr → progress 28%
May → progress 29%
          ↓
      Risk Trend
          ↓
   Early Warning
```

Add:

- Lag features
- Rolling averages
- Progress velocity
- Expenditure velocity
- Milestone slippage
- Schedule trajectory

Then use time-aware validation.

Example:

```text
Training: 2021–2024
Validation: 2025
Testing: 2026
```

This is much more representative of real future prediction than a random split.

---

# 26. Model Comparison Experiment

The project should explicitly demonstrate:

```text
                    Accuracy
                       |
       +---------------+---------------+
       |                               |
Traditional                       ML
Logistic Regression               XGBoost
       |                               |
       +---------------+---------------+
                       |
               Compare performance
                       |
                       v
             Does ML provide gains?
```

This directly addresses the SIH requirement to assess whether AI/ML offers significant gains over conventional methods.

---

# 27. What We Should NOT Do

### Do not make a chatbot the main product

A chatbot alone does not solve the core problem.

### Do not use deep learning just because it sounds advanced

The available data is structured/tabular. Tree-based ML is a stronger starting point.

### Do not claim future prediction from a single snapshot

Clearly distinguish:

```text
Observed/current risk
```

from:

```text
Validated future prediction
```

### Do not leak target variables

Never allow the model to directly see the answer.

### Do not create arbitrary risk explanations

Use model-derived explanations and documented rules.

### Do not let the LLM hallucinate project facts.

---

# 28. Recommended MVP Development Order

## Sprint 1 — Data

```text
CSV
 ↓
Cleaning
 ↓
EDA
 ↓
Feature engineering
```

## Sprint 2 — ML

```text
Baseline
 ↓
XGBoost
 ↓
Evaluation
 ↓
SHAP
```

## Sprint 3 — Product

```text
Risk Engine
 ↓
API
 ↓
Dashboard
 ↓
Project Detail
```

## Sprint 4 — Intelligence

```text
Early Warning
 ↓
Benchmarking
 ↓
Recommendations
 ↓
LLM Assistant
```

---

# 29. Team Division

### ML/Data Team

Responsible for:

- Data cleaning
- EDA
- Feature engineering
- Model training
- Evaluation
- SHAP

### Backend Team

Responsible for:

- FastAPI
- Database
- Prediction APIs
- Data ingestion
- Authentication

### Frontend Team

Responsible for:

- Dashboard
- Charts
- Filters
- Project detail
- Risk visualization

### AI/LLM Team

Responsible for:

- LLM integration
- Retrieval
- Grounded responses
- Prompt design

### DevOps/Integration

Responsible for:

- Docker
- Deployment
- CI/CD
- Environment configuration

---

# 30. Final Recommended Approach

The strongest practical approach for SIH 26103 is:

```text
                PROJECT DATA
                     ↓
              DATA QUALITY
                     ↓
            FEATURE ENGINEERING
                     ↓
        ┌────────────┴────────────┐
        ↓                         ↓
 COST RISK MODEL            TIME RISK MODEL
 XGBoost/LightGBM            XGBoost/LightGBM
        ↓                         ↓
        └────────────┬────────────┘
                     ↓
             IMPLEMENTATION RISK
                     ↓
                RISK ENGINE
                     ↓
              0–100 RISK SCORE
                     ↓
              SHAP EXPLANATION
                     ↓
              EARLY WARNING
                     ↓
          MONITORING RECOMMENDATION
                     ↓
          ┌──────────┴──────────┐
          ↓                     ↓
      DASHBOARD            LLM ASSISTANT
```

## Final Product Philosophy

> **Predict with ML.  
> Explain with SHAP.  
> Prioritize with risk scoring.  
> Recommend with transparent rules.  
> Communicate with an LLM.**

This combination directly maps the solution to the SIH requirement while keeping the MVP technically realistic and defensible.
