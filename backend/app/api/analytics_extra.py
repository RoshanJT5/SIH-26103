from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..db.session import get_db
from ..models import ModelVersion
from ..services.analytics_extra import (
    cost_drivers,
    ministry_health,
    geography,
    timeline,
    list_models,
    performance,
)

router = APIRouter(tags=["analytics"])


@router.get("/analytics/cost-drivers")
def get_cost_drivers(limit: int = 20, db: Session = Depends(get_db)):
    return {
        "items": cost_drivers(db, limit=limit),
        "methodology": "Average SHAP contribution per feature across stored explanations.",
        "limitations": ["Snapshot classification caveat."],
    }


@router.get("/analytics/ministries/{ministry}/health")
def get_ministry_health(ministry: str, db: Session = Depends(get_db)):
    res = ministry_health(db, ministry)
    if not res:
        raise HTTPException(status_code=404, detail="Ministry not found.")
    return res


@router.get("/analytics/geography")
def get_geography(db: Session = Depends(get_db)):
    return {
        "regions": geography(db),
        "note": "Illustrative map: region aggregates by ministry proxy; not a geographic boundary map.",
        "methodology": "Grouped by ministry; illustrative only.",
    }


@router.get("/projects/{project_id}/timeline")
def get_timeline(project_id: int, db: Session = Depends(get_db)):
    pts = timeline(db, project_id)
    if pts is None:
        raise HTTPException(
            status_code=404, detail="Project not found or no completed snapshots."
        )
    return {
        "project_id": project_id,
        "points": pts,
        "methodology": "Snapshots across completed datasets ordered by dataset_id (time proxy).",
    }


@router.get("/ml/models")
def get_models(db: Session = Depends(get_db)):
    models = list_models(db)
    return {
        "items": [
            {
                "id": m.id,
                "name": m.name,
                "target_type": m.target_type,
                "feature_schema": m.feature_schema,
                "metrics": m.metrics,
                "created_at": m.created_at,
                "training_dataset_id": m.training_dataset_id,
            }
            for m in models
        ]
    }


@router.get("/ml/models/{version_id}")
def get_model(version_id: int, db: Session = Depends(get_db)):
    m = db.get(ModelVersion, version_id)
    if not m:
        raise HTTPException(status_code=404, detail="Model version not found.")
    return {
        "id": m.id,
        "name": m.name,
        "target_type": m.target_type,
        "target_definition": m.target_definition,
        "feature_schema": m.feature_schema,
        "artifact_reference": m.artifact_reference,
        "artifact_checksum": m.artifact_checksum,
        "training_dataset_id": m.training_dataset_id,
        "split_seed": m.split_seed,
        "metrics": m.metrics,
        "calibration_metadata": m.calibration_metadata,
        "created_at": m.created_at,
    }


@router.get("/ml/performance")
def get_performance(db: Session = Depends(get_db)):
    return performance(db)
