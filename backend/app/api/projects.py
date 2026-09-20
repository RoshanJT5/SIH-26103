from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any
import pandas as pd

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import PROJECT_ROOT, get_settings
from ..core.auth import get_current_user
from ..db.session import get_db
from ..models import (
    Dataset,
    EarlyWarning,
    ModelVersion,
    Project,
    ProjectSnapshot,
    RiskPrediction,
)
from ..schemas.project_create import CreateProjectRequest, CreateProjectResponse
from ..schemas.uploads import UploadValidationResponse
from ..services.csv_upload import CsvUploadError, validate_project_csv
from ..services.dataset_init import ensure_demo_dataset_loaded
from ..services.early_warning import generate_for_snapshot
from ..services.features import (
    build_model_feature_row,
    derive_analytical_features,
)
from ..services.ingestion import persist_validated_import
from ..services.risk import (
    RULE_VERSION,
    calculate_risk_score,
    implementation_risk,
)
from ml.training.pipeline import load_model_artifact, predict_probabilities

router = APIRouter(prefix="/projects", tags=["projects"])

ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
}


@router.post("/initialize-demo")
def initialize_demo(
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """1-click baseline loading of the 1,775-project MoSPI dataset."""
    return ensure_demo_dataset_loaded(db)


@router.post("", response_model=CreateProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CreateProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    request: CreateProjectRequest,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(get_current_user),
) -> CreateProjectResponse:
    """Creates a new project record, persists its snapshot, and scores it with the risk engine."""
    code = request.project_code.strip()
    name = request.project_name.strip()
    sector = request.sector.strip()
    ministry = request.ministry.strip()
    agency = request.implementing_agency.strip()

    # Get active dataset or initialize demo
    dataset = db.scalar(
        select(Dataset).where(Dataset.status == "completed").order_by(Dataset.id.desc()).limit(1)
    )
    if dataset is None:
        init_res = ensure_demo_dataset_loaded(db)
        dataset = db.get(Dataset, init_res.get("dataset_id", 1))

    # Create or find Project
    project = db.scalar(select(Project).where(Project.project_code == code))
    if project is None:
        project = Project(project_code=code)
        db.add(project)
        db.flush()

    # Check for existing snapshot in this dataset
    existing_snap = db.scalar(
        select(ProjectSnapshot).where(
            ProjectSnapshot.project_id == project.id,
            ProjectSnapshot.dataset_id == dataset.id,
        )
    )

    max_row = db.scalar(
        select(func.max(ProjectSnapshot.source_row_number)).where(
            ProjectSnapshot.dataset_id == dataset.id
        )
    ) or 0

    if existing_snap is not None:
        snap = existing_snap
        snap.project_name = name
        snap.sector = sector
        snap.ministry = ministry
        snap.implementing_agency = agency
        snap.original_cost_cr = request.original_cost_cr
        snap.revised_cost_cr = request.revised_cost_cr
        snap.expenditure_cr = request.expenditure_cr
        snap.physical_progress_pct = request.physical_progress_pct
        snap.original_commissioning_date = request.original_commissioning_date
        snap.revised_commissioning_date = request.revised_commissioning_date
        snap.sanction_date = request.sanction_date
    else:
        snap = ProjectSnapshot(
            project_id=project.id,
            dataset_id=dataset.id,
            source_row_number=max_row + 1,
            project_name=name,
            sector=sector,
            ministry=ministry,
            implementing_agency=agency,
            original_cost_cr=request.original_cost_cr,
            revised_cost_cr=request.revised_cost_cr,
            expenditure_cr=request.expenditure_cr,
            physical_progress_pct=request.physical_progress_pct,
            original_commissioning_date=request.original_commissioning_date,
            revised_commissioning_date=request.revised_commissioning_date,
            sanction_date=request.sanction_date,
            raw_values={},
            quality_flags=[],
        )
        db.add(snap)
    db.flush()

    # Run feature derivation and scoring
    analytical = derive_analytical_features(
        snap,
        source_as_of_date=dataset.source_as_of_date,
    )

    versions = db.scalars(
        select(ModelVersion)
        .where(ModelVersion.training_dataset_id == dataset.id)
        .order_by(ModelVersion.id.desc())
    ).all()
    cost_version = next((v for v in versions if v.target_type == "cost" and v.metrics.get("selected")), None)
    time_version = next((v for v in versions if v.target_type == "time" and v.metrics.get("selected")), None)

    cost_probability = None
    time_probability = None

    if cost_version:
        try:
            art_path = Path(cost_version.artifact_reference)
            full_path = art_path if art_path.is_absolute() else PROJECT_ROOT / art_path
            cost_art = load_model_artifact(full_path)
            cost_row = pd.DataFrame([build_model_feature_row(snap, analytical, "cost")])
            cost_probability = Decimal(str(float(predict_probabilities(cost_art, cost_row)[0]))).quantize(Decimal("0.0000001"))
        except Exception:
            pass

    if time_version:
        try:
            art_path = Path(time_version.artifact_reference)
            full_path = art_path if art_path.is_absolute() else PROJECT_ROOT / art_path
            time_art = load_model_artifact(full_path)
            time_row = pd.DataFrame([build_model_feature_row(snap, analytical, "time")])
            time_probability = Decimal(str(float(predict_probabilities(time_art, time_row)[0]))).quantize(Decimal("0.0000001"))
        except Exception:
            pass

    # Heuristic calibrated fallbacks if trained models are absent
    if cost_probability is None:
        cost_esc = analytical.cost_escalation_pct or Decimal("0")
        exp_ratio = analytical.expenditure_to_original_cost_ratio or Decimal("0")
        prog_ratio = (snap.physical_progress_pct or Decimal("0")) / Decimal("100")
        heuristic_cost = min(Decimal("0.95"), max(Decimal("0.05"), (cost_esc / Decimal("100")) * Decimal("0.5") + max(Decimal("0"), exp_ratio - prog_ratio)))
        cost_probability = heuristic_cost.quantize(Decimal("0.0000001"))

    if time_probability is None:
        sched_days = analytical.schedule_revision_days or 0
        heuristic_time = min(Decimal("0.95"), max(Decimal("0.05"), Decimal(str(min(sched_days, 1000) / 1000))))
        time_probability = heuristic_time.quantize(Decimal("0.0000001"))

    impl = implementation_risk(snap, source_as_of_date=dataset.source_as_of_date)
    risk_res = calculate_risk_score(cost_probability, time_probability, impl.score)

    pred = db.scalar(
        select(RiskPrediction).where(
            RiskPrediction.snapshot_id == snap.id,
            RiskPrediction.rule_version == RULE_VERSION,
        )
    )
    if pred is None:
        pred = RiskPrediction(
            snapshot_id=snap.id,
            cost_model_version_id=cost_version.id if cost_version else None,
            time_model_version_id=time_version.id if time_version else None,
            rule_version=RULE_VERSION,
        )
        db.add(pred)

    pred.cost_risk_probability = cost_probability
    pred.time_risk_probability = time_probability
    pred.implementation_score = impl.score
    pred.overall_score = risk_res.overall_score
    pred.risk_band = risk_res.band
    pred.availability_status = risk_res.availability_status
    db.flush()

    # Generate Early Warnings
    for typ, sev, title, evidence, review in generate_for_snapshot(db, snap, pred):
        dk = f"{snap.project_id}:{snap.dataset_id}:{typ}"
        existing_ew = db.scalar(select(EarlyWarning).where(EarlyWarning.deduplication_key == dk))
        if not existing_ew:
            ew = EarlyWarning(
                project_id=snap.project_id,
                dataset_id=snap.dataset_id,
                snapshot_id=snap.id,
                prediction_id=pred.id,
                type=typ,
                severity=sev,
                title=title,
                description=title,
                evidence=evidence,
                recommended_review=review,
                status="open",
                deduplication_key=dk,
            )
            db.add(ew)

    db.commit()

    return CreateProjectResponse(
        project_id=project.id,
        project_code=project.project_code,
        project_name=snap.project_name,
        snapshot_id=snap.id,
        sector=snap.sector,
        ministry=snap.ministry,
        implementing_agency=snap.implementing_agency,
        overall_score=pred.overall_score,
        risk_band=pred.risk_band,
        cost_risk_probability=pred.cost_risk_probability,
        time_risk_probability=pred.time_risk_probability,
        implementation_score=pred.implementation_score,
        redirect_url=f"/projects/{project.id}",
        message=f"Project {project.project_code} created and scored successfully.",
    )


@router.post("/upload", response_model=UploadValidationResponse, status_code=status.HTTP_200_OK)
async def upload_project_csv(
    file: Annotated[UploadFile, File()],
    source_as_of_date: Annotated[date | None, Form()] = None,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(get_current_user),
) -> UploadValidationResponse:
    settings = get_settings()
    filename = Path(file.filename or "").name

    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only .csv project reports are accepted.")
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported CSV content type: {file.content_type}.")

    content = await file.read(settings.max_upload_bytes + 1)
    await file.close()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"CSV exceeds the {settings.max_upload_bytes}-byte upload limit.",
        )

    try:
        parsed = validate_project_csv(content)
    except CsvUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    checksum = sha256(content).hexdigest()
    persisted = persist_validated_import(
        db,
        parsed=parsed,
        source_name=filename,
        checksum=checksum,
        source_as_of_date=source_as_of_date,
    )
    dataset = persisted.dataset

    # Auto-score newly ingested datasets
    try:
        from ml.training.score import score_dataset
        from ..services.early_warning import ensure_warnings
        score_dataset(db, dataset_id=dataset.id, analysis_date=source_as_of_date)
        ensure_warnings(db)
    except Exception:
        pass

    return UploadValidationResponse(
        dataset_id=dataset.id,
        filename=filename,
        size_bytes=len(content),
        status=dataset.status,
        idempotent=not persisted.created,
        checksum=checksum,
        source_as_of_date=dataset.source_as_of_date,
        imported_at=dataset.imported_at,
        preamble_rows=parsed.structure.preamble_rows,
        record_count=parsed.structure.record_count,
        accepted_count=dataset.accepted_count,
        rejected_count=dataset.rejected_count,
        issue_count=persisted.issue_count,
        source_columns=parsed.structure.source_columns,
        canonical_columns=parsed.structure.canonical_columns,
    )
