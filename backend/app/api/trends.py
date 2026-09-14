from typing import Annotated
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.trends import (
    RiskTrendsResponse,
    TrendItem,
    Page,
    RISK_TREND_RULES_VERSION,
)
from ..services.trends import get_trends

router = APIRouter(tags=["risk"])


@router.get(
    "/risk/trends",
    response_model=RiskTrendsResponse,
    summary="Risk trends across snapshots",
    description="History across completed snapshots matched by project_id. Thresholds: improving change<=-5, stable -5<change<=5, watch 5<change<=10, deteriorating 10<change<=20, rapid_deterioration change>20. Version risk-trends-v1.",
)
def risk_trends(
    dataset_id: int | None = None,
    project_id: int | None = None,
    sector: str | None = None,
    ministry: str | None = None,
    min_change: Annotated[
        Decimal | None, Query(description="Minimum score_change")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
):
    items, total = get_trends(
        db,
        dataset_id=dataset_id,
        project_id=project_id,
        sector=sector,
        ministry=ministry,
        min_change=min_change,
        limit=limit,
        offset=offset,
    )
    return RiskTrendsResponse(
        version=RISK_TREND_RULES_VERSION,
        thresholds={
            "improving": "change <= -5",
            "stable": "-5 < change <= 5",
            "watch": "5 < change <= 10",
            "deteriorating": "10 < change <= 20",
            "rapid_deterioration": "change > 20",
        },
        items=[TrendItem(**it) for it in items],
        page=Page(offset=offset, limit=limit, total=total),
    )
