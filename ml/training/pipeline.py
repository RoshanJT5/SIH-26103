from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sqlalchemy import select
from sqlalchemy.orm import Session
from xgboost import XGBClassifier

from backend.app.core.config import PROJECT_ROOT
from backend.app.models import Dataset, ModelVersion, ProjectSnapshot
from backend.app.services.features import (
    LABEL_DEFINITIONS,
    MODEL_FEATURE_SCHEMAS,
    TargetType,
    build_training_frame,
    derive_target_label,
    fit_model_preprocessor,
)

DEFAULT_SPLIT_SEED = 42
MIN_ELIGIBLE_SAMPLES = 100
MIN_CLASS_SAMPLES = 20


class TrainingUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatasetSplit:
    train: np.ndarray
    validation: np.ndarray
    test: np.ndarray


@dataclass(frozen=True)
class CandidateResult:
    name: str
    validation_metrics: dict[str, Any]
    test_metrics: dict[str, Any]
    model_version_id: int
    artifact_reference: str
    selected: bool


@dataclass(frozen=True)
class TargetTrainingResult:
    target: TargetType
    status: str
    reason: str | None
    selected_candidate: str | None
    eligible_count: int
    class_counts: dict[str, int]
    split_counts: dict[str, int]
    candidates: list[CandidateResult]
    shap_artifact_reference: str | None


def _json_safe(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def create_group_safe_split(
    labels: pd.Series,
    project_ids: list[int],
    *,
    seed: int = DEFAULT_SPLIT_SEED,
) -> DatasetSplit:
    if len(labels) != len(project_ids):
        raise ValueError("Labels and project IDs must have equal lengths.")
    if len(labels) < MIN_ELIGIBLE_SAMPLES:
        raise TrainingUnavailableError(
            f"Need at least {MIN_ELIGIBLE_SAMPLES} eligible records; found {len(labels)}."
        )

    class_counts = labels.value_counts()
    if len(class_counts) != 2 or int(class_counts.min()) < MIN_CLASS_SAMPLES:
        raise TrainingUnavailableError(
            f"Both classes need at least {MIN_CLASS_SAMPLES} eligible records; found {class_counts.to_dict()}."
        )

    group_frame = pd.DataFrame({"project_id": project_ids, "label": labels.to_numpy()})
    conflicting = group_frame.groupby("project_id")["label"].nunique()
    if (conflicting > 1).any():
        raise TrainingUnavailableError("A project has conflicting target labels across snapshots.")
    groups = group_frame.drop_duplicates("project_id")
    if len(groups) < MIN_ELIGIBLE_SAMPLES:
        raise TrainingUnavailableError(
            f"Need at least {MIN_ELIGIBLE_SAMPLES} distinct projects; found {len(groups)}."
        )

    train_validation_groups, test_groups = train_test_split(
        groups,
        test_size=0.20,
        random_state=seed,
        stratify=groups["label"],
    )
    train_groups, validation_groups = train_test_split(
        train_validation_groups,
        test_size=0.25,
        random_state=seed,
        stratify=train_validation_groups["label"],
    )

    project_id_array = np.asarray(project_ids)
    split = DatasetSplit(
        train=np.flatnonzero(np.isin(project_id_array, train_groups["project_id"])),
        validation=np.flatnonzero(np.isin(project_id_array, validation_groups["project_id"])),
        test=np.flatnonzero(np.isin(project_id_array, test_groups["project_id"])),
    )
    train_ids = set(project_id_array[split.train])
    validation_ids = set(project_id_array[split.validation])
    test_ids = set(project_id_array[split.test])
    if train_ids & validation_ids or train_ids & test_ids or validation_ids & test_ids:
        raise AssertionError("Project groups overlap between model splits.")
    return split


def classification_metrics(labels: pd.Series | np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    y_true = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    predictions = (probabilities >= 0.5).astype(int)
    undefined: list[str] = []

    if len(np.unique(y_true)) < 2:
        roc_auc = None
        pr_auc = None
        undefined.extend(["roc_auc", "pr_auc"])
    else:
        roc_auc = float(roc_auc_score(y_true, probabilities))
        pr_auc = float(average_precision_score(y_true, probabilities))

    return {
        "threshold": 0.5,
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "confusion_matrix": confusion_matrix(y_true, predictions, labels=[0, 1]).tolist(),
        "calibration": {
            "brier_score": float(brier_score_loss(y_true, probabilities)),
            "log_loss": float(log_loss(y_true, probabilities, labels=[0, 1])),
        },
        "undefined_metrics": undefined,
        "record_count": int(len(y_true)),
    }


def _candidate_models(y_train: pd.Series, seed: int) -> dict[str, Any]:
    negative, positive = np.bincount(y_train.to_numpy(dtype=int), minlength=2)
    scale_pos_weight = float(negative / positive) if positive else 1.0
    return {
        "logistic_regression": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=seed,
        ),
        "xgboost": XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=2,
            reg_lambda=1.0,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=seed,
            n_jobs=1,
            scale_pos_weight=scale_pos_weight,
        ),
    }


def _artifact_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_reference(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_model_artifact(path: Path) -> dict[str, Any]:
    artifact = joblib.load(path)
    required = {
        "target",
        "feature_names",
        "preprocessor",
        "calibrated_model",
        "classification_threshold",
    }
    missing = sorted(required - set(artifact))
    if missing:
        raise ValueError(f"Invalid model artifact; missing: {', '.join(missing)}")
    return artifact


def predict_probabilities(artifact: dict[str, Any], rows: pd.DataFrame) -> np.ndarray:
    feature_names = tuple(artifact["feature_names"])
    missing = sorted(set(feature_names) - set(rows.columns))
    if missing:
        raise ValueError(f"Missing inference features: {', '.join(missing)}")
    transformed = artifact["preprocessor"].transform(rows.loc[:, feature_names])
    return np.asarray(artifact["calibrated_model"].predict_proba(transformed)[:, 1])


def _dense(values):
    return values.toarray() if hasattr(values, "toarray") else np.asarray(values)


def write_shap_report(
    *,
    base_model: Any,
    model_name: str,
    transformed_train,
    transformed_test,
    transformed_feature_names: list[str],
    test_snapshot_ids: list[int],
    destination: Path,
) -> dict[str, Any]:
    test_values = _dense(transformed_test)
    train_values = _dense(transformed_train)
    if model_name == "xgboost":
        explainer = shap.TreeExplainer(base_model, model_output="raw")
        values = np.asarray(explainer.shap_values(test_values))
        baseline = np.asarray(explainer.expected_value)
    else:
        background = train_values[: min(250, len(train_values))]
        explainer = shap.LinearExplainer(base_model, background)
        values = np.asarray(explainer.shap_values(test_values))
        baseline = np.asarray(explainer.expected_value)

    if values.ndim == 3:
        values = values[:, :, -1]
    baseline_value = float(baseline.reshape(-1)[-1])
    mean_absolute = np.mean(np.abs(values), axis=0)
    global_order = np.argsort(mean_absolute)[::-1]
    global_importance = [
        {"feature": transformed_feature_names[index], "mean_absolute_shap": float(mean_absolute[index])}
        for index in global_order
    ]

    local_explanations = []
    for row_index, snapshot_id in enumerate(test_snapshot_ids):
        order = np.argsort(np.abs(values[row_index]))[::-1][:10]
        local_explanations.append(
            {
                "snapshot_id": snapshot_id,
                "top_contributions": [
                    {
                        "feature": transformed_feature_names[index],
                        "feature_value": float(test_values[row_index, index]),
                        "shap_contribution": float(values[row_index, index]),
                    }
                    for index in order
                ],
            }
        )

    report = {
        "output_scale": "raw",
        "baseline_value": baseline_value,
        "scope": "selected component model only; values do not explain the future blended risk score",
        "global_importance": global_importance,
        "local_explanations": local_explanations,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(_json_safe(report), indent=2), encoding="utf-8")
    return report


def train_target(
    session: Session,
    *,
    dataset: Dataset,
    snapshots: list[ProjectSnapshot],
    target: TargetType,
    analysis_date: date | None,
    artifact_root: Path,
    seed: int = DEFAULT_SPLIT_SEED,
) -> TargetTrainingResult:
    frame, labels, eligibility = build_training_frame(
        snapshots,
        target,
        source_as_of_date=dataset.source_as_of_date,
        requested_analysis_date=analysis_date,
    )
    eligible_snapshots = [snapshot for snapshot in snapshots if derive_target_label(snapshot, target).eligible]
    project_ids = [snapshot.project_id for snapshot in eligible_snapshots]
    snapshot_ids = [snapshot.id for snapshot in eligible_snapshots]
    class_counts = {str(key): int(value) for key, value in labels.value_counts().sort_index().items()}

    try:
        split = create_group_safe_split(labels, project_ids, seed=seed)
    except TrainingUnavailableError as exc:
        return TargetTrainingResult(
            target=target,
            status="unavailable",
            reason=str(exc),
            selected_candidate=None,
            eligible_count=eligibility.eligible,
            class_counts=class_counts,
            split_counts={},
            candidates=[],
            shap_artifact_reference=None,
        )

    x_train, y_train = frame.iloc[split.train], labels.iloc[split.train]
    x_validation, y_validation = frame.iloc[split.validation], labels.iloc[split.validation]
    x_test, y_test = frame.iloc[split.test], labels.iloc[split.test]
    preprocessor = fit_model_preprocessor(x_train, target)
    transformed_train = preprocessor.transform(x_train)
    transformed_validation = preprocessor.transform(x_validation)
    transformed_test = preprocessor.transform(x_test)
    transformed_names = list(preprocessor.transformer.get_feature_names_out())

    candidate_state: dict[str, dict[str, Any]] = {}
    for name, base_model in _candidate_models(y_train, seed).items():
        base_model.fit(transformed_train, y_train)
        validation_probabilities = base_model.predict_proba(transformed_validation)[:, 1]
        validation_metrics = classification_metrics(y_validation, validation_probabilities)

        calibrated_model = CalibratedClassifierCV(FrozenEstimator(base_model), method="sigmoid")
        calibrated_model.fit(transformed_validation, y_validation)
        test_probabilities = calibrated_model.predict_proba(transformed_test)[:, 1]
        test_metrics = classification_metrics(y_test, test_probabilities)
        candidate_state[name] = {
            "base_model": base_model,
            "calibrated_model": calibrated_model,
            "validation_metrics": validation_metrics,
            "test_metrics": test_metrics,
        }

    selected_name = max(
        candidate_state,
        key=lambda name: (
            candidate_state[name]["validation_metrics"]["pr_auc"] or -1,
            candidate_state[name]["validation_metrics"]["recall"],
        ),
    )
    split_counts = {
        "train": int(len(split.train)),
        "validation": int(len(split.validation)),
        "test": int(len(split.test)),
    }
    split_snapshot_ids = {
        "train": [snapshot_ids[index] for index in split.train],
        "validation": [snapshot_ids[index] for index in split.validation],
        "test": [snapshot_ids[index] for index in split.test],
    }
    split_membership_checksum = hashlib.sha256(
        json.dumps(split_snapshot_ids, sort_keys=True).encode("utf-8")
    ).hexdigest()
    run_directory = artifact_root / f"dataset_{dataset.id}" / target
    run_directory.mkdir(parents=True, exist_ok=True)
    pending_versions: list[tuple[str, ModelVersion, Path]] = []

    for name, state in candidate_state.items():
        artifact_path = run_directory / f"{name}_seed_{seed}.joblib"
        joblib.dump(
            {
                "target": target,
                "candidate": name,
                "dataset_id": dataset.id,
                "dataset_checksum": dataset.checksum,
                "analysis_date": analysis_date,
                "split_seed": seed,
                "split_snapshot_ids": split_snapshot_ids,
                "split_membership_checksum": split_membership_checksum,
                "feature_names": list(preprocessor.feature_names),
                "transformed_feature_names": transformed_names,
                "preprocessor": preprocessor.transformer,
                "base_model": state["base_model"],
                "calibrated_model": state["calibrated_model"],
                "classification_threshold": 0.5,
            },
            artifact_path,
        )
        relative_reference = _artifact_reference(artifact_path)
        model_name = f"{target}_{name}"
        target_definition = {
            **LABEL_DEFINITIONS[target],
            "eligibility_counts": asdict(eligibility),
        }
        feature_schema = {
                "version": MODEL_FEATURE_SCHEMAS[target].version,
                "raw_features": list(preprocessor.feature_names),
                "transformed_features": transformed_names,
                "analysis_date": analysis_date.isoformat() if analysis_date else None,
                "analysis_date_source": "request" if analysis_date else ("dataset" if dataset.source_as_of_date else "unavailable"),
        }
        metrics = {
                "candidate": name,
                "selected": name == selected_name,
                "selection_metric": "validation_pr_auc_then_recall",
                "validation_uncalibrated": state["validation_metrics"],
                "test_calibrated": state["test_metrics"],
                "split_counts": split_counts,
                "split_membership_checksum": split_membership_checksum,
                "claim": "snapshot risk-classification estimate; not validated future forecasting",
        }
        calibration_metadata = {
                "method": "sigmoid",
                "fit_partition": "validation",
                "test_partition_used": False,
        }
        version = session.scalar(
            select(ModelVersion).where(
                ModelVersion.name == model_name,
                ModelVersion.target_type == target,
                ModelVersion.training_dataset_id == dataset.id,
                ModelVersion.split_seed == seed,
            )
        )
        if version is None:
            version = ModelVersion(
                name=model_name,
                target_type=target,
                target_definition=target_definition,
                feature_schema=feature_schema,
                artifact_reference=relative_reference,
                artifact_checksum=_artifact_checksum(artifact_path),
                training_dataset_id=dataset.id,
                split_seed=seed,
                metrics=metrics,
                calibration_metadata=calibration_metadata,
            )
            session.add(version)
        else:
            version.target_definition = target_definition
            version.feature_schema = feature_schema
            version.artifact_reference = relative_reference
            version.artifact_checksum = _artifact_checksum(artifact_path)
            version.metrics = metrics
            version.calibration_metadata = calibration_metadata
        pending_versions.append((name, version, artifact_path))

    session.flush()
    selected_state = candidate_state[selected_name]
    shap_path = run_directory / f"{selected_name}_seed_{seed}_shap.json"
    shap_report = write_shap_report(
        base_model=selected_state["base_model"],
        model_name=selected_name,
        transformed_train=transformed_train,
        transformed_test=transformed_test,
        transformed_feature_names=transformed_names,
        test_snapshot_ids=[snapshot_ids[index] for index in split.test],
        destination=shap_path,
    )

    candidates: list[CandidateResult] = []
    for name, version, artifact_path in pending_versions:
        if name == selected_name:
            version.calibration_metadata = {
                **(version.calibration_metadata or {}),
                "shap_artifact_reference": _artifact_reference(shap_path),
                "shap_output_scale": shap_report["output_scale"],
                "shap_baseline_value": shap_report["baseline_value"],
            }
        candidates.append(
            CandidateResult(
                name=name,
                validation_metrics=candidate_state[name]["validation_metrics"],
                test_metrics=candidate_state[name]["test_metrics"],
                model_version_id=version.id,
                artifact_reference=_artifact_reference(artifact_path),
                selected=name == selected_name,
            )
        )
    session.commit()

    return TargetTrainingResult(
        target=target,
        status="available",
        reason=None,
        selected_candidate=selected_name,
        eligible_count=eligibility.eligible,
        class_counts=class_counts,
        split_counts=split_counts,
        candidates=candidates,
        shap_artifact_reference=_artifact_reference(shap_path),
    )


def train_dataset(
    session: Session,
    *,
    dataset_id: int,
    analysis_date: date | None,
    artifact_root: Path,
    seed: int = DEFAULT_SPLIT_SEED,
) -> list[TargetTrainingResult]:
    dataset = session.scalar(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "completed")
    )
    if dataset is None:
        raise ValueError(f"Completed dataset {dataset_id} was not found.")
    snapshots = list(
        session.scalars(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.dataset_id == dataset_id)
            .order_by(ProjectSnapshot.project_id)
        )
    )
    results = []
    for target in ("cost", "time"):
        results.append(
            train_target(
                session,
                dataset=dataset,
                snapshots=snapshots,
                target=target,
                analysis_date=analysis_date,
                artifact_root=artifact_root,
                seed=seed,
            )
        )
    return results
