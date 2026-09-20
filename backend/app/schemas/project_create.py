from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    project_code: str = Field(min_length=1, max_length=64, description="Unique project code (e.g. MOR-2026-001)")
    project_name: str = Field(min_length=2, max_length=500, description="Project title")
    sector: str = Field(min_length=1, max_length=255, description="Infrastructure sector")
    ministry: str = Field(min_length=1, max_length=255, description="Line ministry")
    implementing_agency: str = Field(min_length=1, max_length=500, description="Implementing agency")
    original_cost_cr: Decimal = Field(gt=0, description="Original cost in ₹ Crore")
    revised_cost_cr: Decimal | None = Field(default=None, ge=0, description="Revised cost in ₹ Crore")
    expenditure_cr: Decimal = Field(ge=0, description="Expenditure in ₹ Crore")
    physical_progress_pct: Decimal = Field(ge=0, le=100, description="Physical progress percentage")
    original_commissioning_date: date = Field(description="Original commissioning date")
    revised_commissioning_date: date | None = Field(default=None, description="Revised commissioning date")
    sanction_date: date | None = Field(default=None, description="Sanction date")


class CreateProjectResponse(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    snapshot_id: int
    sector: str
    ministry: str
    implementing_agency: str
    overall_score: Decimal | None = None
    risk_band: str | None = None
    cost_risk_probability: Decimal | None = None
    time_risk_probability: Decimal | None = None
    implementation_score: Decimal | None = None
    redirect_url: str
    message: str
