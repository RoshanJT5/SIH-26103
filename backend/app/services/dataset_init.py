from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import PROJECT_ROOT
from ..models import Dataset, Project, ProjectSnapshot, RiskPrediction
from .csv_upload import validate_project_csv
from .ingestion import persist_validated_import
from .early_warning import ensure_warnings


def ensure_demo_dataset_loaded(session: Session) -> dict[str, Any]:
    """Ensures the baseline demonstration MoSPI dataset (1,775 projects) is loaded, trained, and scored."""
    existing_completed = session.scalar(
        select(Dataset).where(Dataset.status == "completed").limit(1)
    )
    if existing_completed is not None:
        proj_count = session.scalar(select(func.count()).select_from(Project)) or 0
        pred_count = session.scalar(select(func.count()).select_from(RiskPrediction)) or 0
        return {
            "status": "already_initialized",
            "dataset_id": existing_completed.id,
            "project_count": proj_count,
            "prediction_count": pred_count,
            "message": "Demo dataset is already loaded and scored.",
        }

    csv_path = PROJECT_ROOT / "DATA" / "Projects_Report.csv"
    if not csv_path.exists():
        return {
            "status": "missing_file",
            "message": f"Source CSV file not found at {csv_path}",
        }

    content = csv_path.read_bytes()
    parsed = validate_project_csv(content)
    checksum = sha256(content).hexdigest()
    as_of = date(2026, 9, 1)

    persisted = persist_validated_import(
        session,
        parsed=parsed,
        source_name="Projects_Report.csv",
        checksum=checksum,
        source_as_of_date=as_of,
    )
    dataset_id = persisted.dataset.id

    from ml.training.pipeline import train_dataset
    from ml.training.score import score_dataset

    train_results = train_dataset(
        session,
        dataset_id=dataset_id,
        analysis_date=as_of,
        artifact_root=PROJECT_ROOT / "artifacts" / "models",
        seed=42,
    )

    scored_count = score_dataset(
        session,
        dataset_id=dataset_id,
        analysis_date=as_of,
    )

    ensure_warnings(session)

    return {
        "status": "initialized",
        "dataset_id": dataset_id,
        "models_trained": len(train_results),
        "scored_projects": scored_count,
        "message": f"Successfully initialized MoSPI portfolio with {scored_count} scored projects.",
    }
