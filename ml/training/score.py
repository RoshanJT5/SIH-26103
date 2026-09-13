from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import PROJECT_ROOT
from backend.app.db.session import SessionLocal
from backend.app.models import Dataset, ModelVersion, ProjectSnapshot, RiskPrediction
from backend.app.services.features import build_model_feature_row, derive_analytical_features
from backend.app.services.risk import RULE_VERSION, calculate_risk_score, implementation_risk
from ml.training.pipeline import load_model_artifact, predict_probabilities


def _selected_model(session: Session, dataset_id: int, target: str) -> ModelVersion | None:
    versions = session.scalars(
        select(ModelVersion)
        .where(ModelVersion.training_dataset_id == dataset_id, ModelVersion.target_type == target)
        .order_by(ModelVersion.id.desc())
    ).all()
    return next((version for version in versions if version.metrics.get("selected") is True), None)


def _artifact_path(version: ModelVersion) -> Path:
    path = Path(version.artifact_reference)
    return path if path.is_absolute() else PROJECT_ROOT / path


def score_dataset(
    session: Session,
    *,
    dataset_id: int,
    analysis_date: date | None = None,
    rule_version: str = RULE_VERSION,
) -> int:
    dataset = session.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "completed"))
    if dataset is None:
        raise ValueError(f"Completed dataset {dataset_id} was not found.")
    snapshots = session.scalars(
        select(ProjectSnapshot).where(ProjectSnapshot.dataset_id == dataset_id).order_by(ProjectSnapshot.id.asc())
    ).all()
    cost_version = _selected_model(session, dataset_id, "cost")
    time_version = _selected_model(session, dataset_id, "time")
    cost_artifact = load_model_artifact(_artifact_path(cost_version)) if cost_version else None
    time_artifact = load_model_artifact(_artifact_path(time_version)) if time_version else None
    scored = 0

    for snapshot in snapshots:
        analytical = derive_analytical_features(
            snapshot,
            source_as_of_date=dataset.source_as_of_date,
            requested_analysis_date=analysis_date,
        )
        cost_probability = None
        if cost_artifact is not None:
            cost_row = pd.DataFrame([build_model_feature_row(snapshot, analytical, "cost")])
            cost_probability = Decimal(str(float(predict_probabilities(cost_artifact, cost_row)[0]))).quantize(Decimal("0.0000001"))
        time_probability = None
        if time_artifact is not None:
            time_row = pd.DataFrame([build_model_feature_row(snapshot, analytical, "time")])
            time_probability = Decimal(str(float(predict_probabilities(time_artifact, time_row)[0]))).quantize(Decimal("0.0000001"))

        implementation = implementation_risk(
            snapshot,
            source_as_of_date=dataset.source_as_of_date,
            analysis_date=analysis_date,
        )
        result = calculate_risk_score(cost_probability, time_probability, implementation.score)
        existing = session.scalar(
            select(RiskPrediction).where(
                RiskPrediction.snapshot_id == snapshot.id,
                RiskPrediction.cost_model_version_id == (cost_version.id if cost_version else None),
                RiskPrediction.time_model_version_id == (time_version.id if time_version else None),
                RiskPrediction.rule_version == rule_version,
            )
        )
        prediction = existing or RiskPrediction(
            snapshot_id=snapshot.id,
            cost_model_version_id=cost_version.id if cost_version else None,
            time_model_version_id=time_version.id if time_version else None,
            rule_version=rule_version,
        )
        prediction.cost_risk_probability = cost_probability
        prediction.time_risk_probability = time_probability
        prediction.implementation_score = implementation.score
        prediction.overall_score = result.overall_score
        prediction.risk_band = result.band
        prediction.availability_status = result.availability_status
        session.add(prediction)
        scored += 1

    session.commit()
    return scored


def main() -> None:
    parser = argparse.ArgumentParser(description="Score completed project snapshots with selected trained models.")
    parser.add_argument("--dataset-id", type=int, required=True)
    parser.add_argument("--analysis-date", type=date.fromisoformat)
    args = parser.parse_args()
    with SessionLocal() as session:
        count = score_dataset(session, dataset_id=args.dataset_id, analysis_date=args.analysis_date)
    print(json.dumps({"dataset_id": args.dataset_id, "scored_snapshots": count, "rule_version": RULE_VERSION}, indent=2))


if __name__ == "__main__":
    main()
