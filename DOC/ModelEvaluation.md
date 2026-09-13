# Snapshot Model Evaluation

Training run: dataset 1, seed 42, explicit analysis date 2026-09-13.

These models classify cost/time overrun labels visible in the supplied project snapshot. They are not validated forecasts of future outcomes. Historical pre-outcome snapshots are required before making forecasting claims.

## Evaluation protocol

- Cost and time targets use their own eligible populations.
- Each target uses one reproducible, project-group-safe 60/20/20 train/validation/test split shared by logistic regression and XGBoost.
- Imputation, one-hot encoding, and numeric scaling are fitted only on the training partition.
- Candidate selection uses validation PR-AUC, then validation recall as a tie-breaker.
- Sigmoid calibration is fitted on validation data after the base model is trained.
- The test partition is used once for final reporting. The classification threshold remains fixed at 0.5.

| Target | Eligible | Train | Validation | Test | Class 0 | Class 1 |
|---|---:|---:|---:|---:|---:|---:|
| Cost | 942 | 564 | 189 | 189 | 407 | 535 |
| Time | 1,427 | 855 | 286 | 286 | 298 | 1,129 |

## Held-out calibrated test results

| Target | Candidate | Selected from validation | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier | Log loss |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Cost | Logistic regression | No | 0.7636 | 0.7850 | 0.7742 | 0.8160 | 0.8626 | 0.1803 | 0.5358 |
| Cost | XGBoost | Yes | 0.7478 | 0.8037 | 0.7748 | 0.8026 | 0.8599 | 0.1805 | 0.5364 |
| Time | Logistic regression | No | 0.9208 | 0.9779 | 0.9485 | 0.9621 | 0.9897 | 0.0679 | 0.2281 |
| Time | XGBoost | Yes | 0.9234 | 0.9602 | 0.9414 | 0.9529 | 0.9857 | 0.0706 | 0.2371 |

The validation procedure selected XGBoost for both targets. The held-out results show that logistic regression performs slightly better on several test metrics, especially for time risk. The test results were not used to reverse the predeclared selection. This dataset therefore does not demonstrate a clear general performance gain from XGBoost over the statistical baseline.

Cost confusion matrices (`[[TN, FP], [FN, TP]]`): logistic `[[56, 26], [23, 84]]`; XGBoost `[[53, 29], [21, 86]]`.

Time confusion matrices: logistic `[[41, 19], [5, 221]]`; XGBoost `[[42, 18], [9, 217]]`.

## Artifacts and explainability

The SQLite model registry contains four version records: one logistic and one XGBoost artifact per target. Each record stores the dataset, target/feature definitions, feature order, analysis date, split seed, split-membership checksum, metrics, artifact checksum, calibration partition, and selection result.

The selected models have global mean-absolute SHAP importance and local top-ten contributions for every held-out project. SHAP values and baselines use the component model's raw output scale. They must not be displayed as probability percentage points or used as explanations of the later blended overall risk score.
