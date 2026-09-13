# Feature and Label Definitions

Version: `snapshot-features-v1` / `snapshot-labels-v1`

These definitions apply to the project-level snapshot MVP. They support current-risk classification and do not establish future forecasting performance.

## Analytical features

| Feature | Definition | Unavailable when |
|---|---|---|
| `cost_increase_cr` | revised cost − original cost | revised cost is null or zero |
| `cost_escalation_pct` | cost increase ÷ original cost × 100 | revised cost is null/zero or original cost is nonpositive |
| `expenditure_to_original_cost_ratio` | expenditure ÷ original cost | original cost is nonpositive |
| `expenditure_to_revised_cost_ratio` | expenditure ÷ revised cost | revised cost is null or zero |
| `schedule_revision_days` | revised commissioning date − original commissioning date | revised date is null |
| `planned_duration_days` | original commissioning date − sanction date | sanction date is null or follows original commissioning |
| `project_age_days` | explicit analysis date − sanction date | sanction/analysis date is null, or analysis precedes sanction |

An API-supplied analysis date takes precedence over the dataset source date. When neither exists, project age remains null and carries the reason `analysis date and dataset source date are unavailable`. Import time is never substituted.

## Target labels

| Target | Eligible records | Positive label | Unknown label |
|---|---|---|---|
| Cost overrun | original cost > 0 and revised cost > 0 | revised cost > original cost | revised cost is missing or zero |
| Time overrun | original and revised commissioning dates present | revised date > original date | revised date is missing |

Unknown labels are excluded from model training and evaluation; they are never imputed as negative outcomes.

## Leakage audit

Both model schemas use sector, ministry, implementing agency, original cost, expenditure, physical progress, expenditure/original-cost ratio, project age, and planned duration. These are snapshot indicators, so model results must retain the snapshot-classification caveat.

The cost model blocks revised cost, cost increase, cost escalation, expenditure/revised-cost ratio, the cost label, project code, project name, and source row number. The time model blocks revised commissioning date, schedule revision days, the time label, and the same identifiers. The training-frame builder emits only allowlisted columns, and the preprocessing builder rejects prohibited fields before fitting imputers or encoders on the supplied training partition.

## Current dataset eligibility

For dataset 1 (`Projects_Report.csv`, 1,775 projects):

| Target | Eligible | Positive | Negative | Unknown |
|---|---:|---:|---:|---:|
| Cost overrun | 942 | 535 | 407 | 833 |
| Time overrun | 1,427 | 1,129 | 298 | 348 |

Cost-derived features are available for 942 projects and schedule revision is available for 1,427. Project age is unavailable for all current records because this import has no source as-of date. Callers may provide an explicit analysis date when the intended analytical date is known.
